"""The RBAC contract, stated once and readably.

The read half pins exact status codes. The write half (added in the final review round:
the matrix used to be GET-only, so nothing here covered the eight permissions whose
misconfiguration would let a lead approve their own mission or a crew member restaff a
roster) asserts *allowed vs denied* rather than an exact code, because a permitted write
can legitimately land on 200, 201 or a 400 domain error depending on fixture state --
what the matrix is for is the 403 boundary. Each write case is set up so nothing but the
permission decides the outcome: object-scoped writes act on the actor's own tenant, and
ownership is arranged to suit (`owned=True` for the progress/edit rules that leads hold
only over their own missions, `owned=False` for review, where the creator is barred from
approving regardless of role).
"""

import datetime as dt

import pytest

from mission_control.missions.factories import MissionFactory
from mission_control.users.factories import SkillFactory, UserFactory
from mission_control.users.roles import Role

pytestmark = pytest.mark.django_db

ROLES = ("director", "mission_lead", "crew_member")

CASES = [
    ("/api/v1/missions/", {"director": 200, "mission_lead": 200, "crew_member": 403}),
    ("/api/v1/crew/", {"director": 200, "mission_lead": 200, "crew_member": 403}),
    ("/api/v1/skills/", {"director": 200, "mission_lead": 200, "crew_member": 200}),
    ("/api/v1/settings/users/", {"director": 200, "mission_lead": 403, "crew_member": 403}),
    ("/api/v1/settings/organisation/", {"director": 200, "mission_lead": 403, "crew_member": 403}),
    ("/api/v1/dashboard/", {"director": 200, "mission_lead": 200, "crew_member": 403}),
    ("/api/v1/me/assignments/", {"director": 403, "mission_lead": 403, "crew_member": 200}),
    ("/api/v1/me/skills/", {"director": 403, "mission_lead": 403, "crew_member": 200}),
]


@pytest.mark.parametrize("url,expectations", CASES)
def test_rbac_matrix(auth_client_for, url, expectations):
    for role, expected in expectations.items():
        user = UserFactory(role=role)
        assert auth_client_for(user).get(url).status_code == expected, f"{role} GET {url}"


# --------------------------------------------------------------------------- writes

ALLOW, DENY = "allow", "deny"
_DATES = {
    "start_date": str(dt.date.today() + dt.timedelta(days=10)),
    "end_date": str(dt.date.today() + dt.timedelta(days=20)),
}


def _mission_url(suffix="", *, owned=True):
    """A mission in the actor's tenant, created by them or by a different lead."""

    def build(user):
        creator = user if owned else UserFactory(role=Role.MISSION_LEAD, tenant=user.tenant)
        mission = MissionFactory(tenant=user.tenant, created_by=creator)
        return f"/api/v1/missions/{mission.id}/{suffix}"

    return build


def _crew_ids(user):
    return [UserFactory(role=Role.CREW_MEMBER, tenant=user.tenant).id]


WRITE_CASES = [
    (
        "mission.create",
        "post",
        lambda user: "/api/v1/missions/",
        lambda user: {"name": "New Op", "min_crew": 1, "max_crew": 2, **_DATES},
        {"director": ALLOW, "mission_lead": ALLOW, "crew_member": DENY},
    ),
    (
        "mission.edit",
        "patch",
        _mission_url(),
        lambda user: {"name": "Renamed"},
        {"director": ALLOW, "mission_lead": ALLOW, "crew_member": DENY},
    ),
    (
        "mission.edit (requirements)",
        "put",
        _mission_url("requirements/"),
        lambda user: {
            "items": [
                {
                    "skill_id": SkillFactory(tenant=user.tenant).id,
                    "min_proficiency": 5,
                    "required_count": 1,
                }
            ]
        },
        {"director": ALLOW, "mission_lead": ALLOW, "crew_member": DENY},
    ),
    (
        "mission.progress",
        "post",
        _mission_url("transitions/"),
        lambda user: {"action": "submit"},
        {"director": ALLOW, "mission_lead": ALLOW, "crew_member": DENY},
    ),
    (
        "mission.review",
        "post",
        _mission_url("transitions/", owned=False),
        lambda user: {"action": "approve"},
        {"director": ALLOW, "mission_lead": DENY, "crew_member": DENY},
    ),
    (
        "assignment.manage",
        "post",
        _mission_url("assignments/"),
        lambda user: {"user_ids": _crew_ids(user)},
        {"director": ALLOW, "mission_lead": ALLOW, "crew_member": DENY},
    ),
    (
        "match.run",
        "post",
        _mission_url("match/"),
        lambda user: {},
        {"director": ALLOW, "mission_lead": ALLOW, "crew_member": DENY},
    ),
    (
        "skill.manage",
        "post",
        lambda user: "/api/v1/skills/",
        lambda user: {"name": "Xenolinguistics"},
        {"director": ALLOW, "mission_lead": DENY, "crew_member": DENY},
    ),
    (
        "user.manage",
        "post",
        lambda user: "/api/v1/settings/users/",
        lambda user: {"email": "matrix@example.com", "name": "Matrix", "role": Role.CREW_MEMBER,
                      "password": "s3cret-pw"},
        {"director": ALLOW, "mission_lead": DENY, "crew_member": DENY},
    ),
    (
        "settings.manage",
        "patch",
        lambda user: "/api/v1/settings/organisation/",
        lambda user: {"name": "Renamed Org"},
        {"director": ALLOW, "mission_lead": DENY, "crew_member": DENY},
    ),
    (
        "assignment.respond",
        "post",
        lambda user: f"/api/v1/assignments/{_respondable_assignment(user)}/respond/",
        lambda user: {"action": "accept"},
        {"director": DENY, "mission_lead": DENY, "crew_member": ALLOW},
    ),
    (
        "own_skills.edit",
        "put",
        lambda user: "/api/v1/me/skills/",
        lambda user: {"items": []},
        {"director": DENY, "mission_lead": DENY, "crew_member": ALLOW},
    ),
]


def _respondable_assignment(user):
    """An assignment the actor may respond to, so only the permission decides.

    Non-crew roles cannot hold one (respond is theirs alone), so they get an id that
    does not exist -- the point of the case is that they are refused before the lookup.
    """
    from mission_control.missions.factories import AssignmentFactory

    if user.role != Role.CREW_MEMBER:
        return 99999999
    mission = MissionFactory(tenant=user.tenant)
    return AssignmentFactory(mission=mission, user=user, tenant=user.tenant).id


@pytest.mark.parametrize(
    "permission,method,url_for,body_for,expectations",
    WRITE_CASES,
    ids=[case[0] for case in WRITE_CASES],
)
def test_rbac_matrix_writes(auth_client_for, permission, method, url_for, body_for, expectations):
    for role in ROLES:
        expected = expectations[role]
        user = UserFactory(role=role)
        client = auth_client_for(user)
        response = getattr(client, method)(url_for(user), body_for(user), format="json")
        label = f"{role} {method.upper()} {permission}"
        if expected is DENY:
            assert response.status_code == 403, f"{label}: expected 403, got {response.status_code}"
        else:
            assert response.status_code != 403, f"{label}: unexpectedly forbidden"


def test_write_matrix_covers_every_permission_that_guards_a_write():
    """The artifact is meant to be the single readable statement of the RBAC contract,
    so an endpoint added behind a new write permission should fail here until it is
    listed.
    """
    from mission_control.users.permissions import Permission

    read_only = {
        Permission.MISSION_VIEW,
        Permission.CREW_VIEW,
        Permission.SKILL_VIEW,
        Permission.SETTINGS_VIEW,
        Permission.DASHBOARD_VIEW,
    }
    covered = {case[0].split(" ")[0] for case in WRITE_CASES}
    assert {str(p) for p in Permission} - read_only == covered
