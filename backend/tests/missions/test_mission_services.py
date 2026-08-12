import datetime as dt

import pytest
from django.core.exceptions import ValidationError
from django.http import Http404
from rest_framework.exceptions import PermissionDenied

from mission_control.common.exceptions import ApplicationError
from mission_control.missions.factories import MissionFactory, MissionRequirementFactory
from mission_control.missions.models import Mission, MissionRequirement, MissionStatus
from mission_control.missions.selectors.missions import (
    mission_get,
    mission_list,
    mission_submitter_id,
)
from mission_control.missions.services.missions import (
    mission_create,
    mission_requirements_set,
    mission_update,
    transition_mission,
)
from mission_control.tenants.context import set_current_tenant_id
from mission_control.users.factories import SkillFactory, UserFactory
from mission_control.users.roles import Role

pytestmark = pytest.mark.django_db


def test_requirements_set_replaces():
    mission = MissionFactory()
    set_current_tenant_id(mission.tenant_id)
    s1, s2 = SkillFactory(tenant=mission.tenant), SkillFactory(tenant=mission.tenant)
    mission_requirements_set(actor=mission.created_by, mission=mission, items=[
        {"skill_id": s1.id, "min_proficiency": 7, "required_count": 1},
        {"skill_id": s2.id, "min_proficiency": 4, "required_count": 2},
    ])
    mission_requirements_set(actor=mission.created_by, mission=mission, items=[
        {"skill_id": s1.id, "min_proficiency": 9, "required_count": 1},
    ])
    rows = MissionRequirement.objects.filter(mission=mission)
    assert [(r.skill_id, r.min_proficiency, r.required_count) for r in rows] == [(s1.id, 9, 1)]


def test_edit_locked_outside_draft_rejected():
    mission = MissionFactory(status=MissionStatus.ACTIVE)
    set_current_tenant_id(mission.tenant_id)
    with pytest.raises(ApplicationError):
        mission_update(actor=mission.created_by, mission=mission, name="Renamed")


def test_archived_skill_rejected_in_requirements():
    mission = MissionFactory()
    set_current_tenant_id(mission.tenant_id)
    archived = SkillFactory(tenant=mission.tenant, is_archived=True)
    with pytest.raises(ApplicationError):
        mission_requirements_set(actor=mission.created_by, mission=mission, items=[
            {"skill_id": archived.id, "min_proficiency": 5, "required_count": 1},
        ])


# --- mission_create ----------------------------------------------------------------


def test_mission_create_stamps_tenant_and_draft_status():
    lead = UserFactory(role=Role.MISSION_LEAD)
    set_current_tenant_id(lead.tenant_id)
    mission = mission_create(
        actor=lead,
        name="Ganymede Survey",
        description="Ice mapping",
        start_date=dt.date(2026, 9, 1),
        end_date=dt.date(2026, 9, 14),
        min_crew=2,
        max_crew=4,
    )
    assert mission.pk is not None
    assert mission.tenant_id == lead.tenant_id
    assert mission.status == MissionStatus.DRAFT
    assert mission.created_by_id == lead.id


@pytest.mark.parametrize(
    ("start", "end", "min_crew", "max_crew"),
    [
        (dt.date(2026, 9, 14), dt.date(2026, 9, 1), 1, 2),  # end before start
        (dt.date(2026, 9, 1), dt.date(2026, 9, 14), 5, 2),  # max below min
        (dt.date(2026, 9, 1), dt.date(2026, 9, 14), 0, 2),  # min below 1
    ],
)
def test_mission_create_check_constraints_surface_as_validation(start, end, min_crew, max_crew):
    """Constraint violations must be ValidationError (-> 400), never an IntegrityError 500."""
    lead = UserFactory(role=Role.MISSION_LEAD)
    set_current_tenant_id(lead.tenant_id)
    with pytest.raises(ValidationError):
        mission_create(
            actor=lead,
            name="Bad dates",
            description="",
            start_date=start,
            end_date=end,
            min_crew=min_crew,
            max_crew=max_crew,
        )
    assert not Mission.objects.exists()


# --- mission_update ----------------------------------------------------------------


def test_mission_update_applies_fields_in_draft():
    mission = MissionFactory()
    set_current_tenant_id(mission.tenant_id)
    updated = mission_update(
        actor=mission.created_by, mission=mission, name="Renamed", min_crew=2, max_crew=5
    )
    updated.refresh_from_db()
    assert (updated.name, updated.min_crew, updated.max_crew) == ("Renamed", 2, 5)


def test_mission_update_allowed_in_rejected():
    mission = MissionFactory(status=MissionStatus.REJECTED)
    set_current_tenant_id(mission.tenant_id)
    assert mission_update(actor=mission.created_by, mission=mission, name="Second try").name == (
        "Second try"
    )


def test_mission_update_validates_constraints():
    mission = MissionFactory()
    set_current_tenant_id(mission.tenant_id)
    with pytest.raises(ValidationError):
        mission_update(
            actor=mission.created_by, mission=mission, end_date=mission.start_date - dt.timedelta(1)
        )


def test_lead_cannot_edit_another_leads_mission():
    mission = MissionFactory()
    set_current_tenant_id(mission.tenant_id)
    other_lead = UserFactory(role=Role.MISSION_LEAD, tenant=mission.tenant)
    with pytest.raises(PermissionDenied):
        mission_update(actor=other_lead, mission=mission, name="Hijacked")


def test_director_may_edit_another_leads_mission():
    mission = MissionFactory()
    set_current_tenant_id(mission.tenant_id)
    director = UserFactory(role=Role.DIRECTOR, tenant=mission.tenant)
    assert mission_update(actor=director, mission=mission, name="Retitled").name == "Retitled"


# --- mission_requirements_set ------------------------------------------------------


def test_requirements_allow_same_skill_at_different_proficiencies():
    mission = MissionFactory()
    set_current_tenant_id(mission.tenant_id)
    skill = SkillFactory(tenant=mission.tenant)
    mission_requirements_set(actor=mission.created_by, mission=mission, items=[
        {"skill_id": skill.id, "min_proficiency": 8, "required_count": 1},
        {"skill_id": skill.id, "min_proficiency": 4, "required_count": 2},
    ])
    assert MissionRequirement.objects.filter(mission=mission).count() == 2


def test_requirements_reject_duplicate_skill_proficiency_pairs():
    mission = MissionFactory()
    set_current_tenant_id(mission.tenant_id)
    skill = SkillFactory(tenant=mission.tenant)
    with pytest.raises(ApplicationError, match="Duplicate"):
        mission_requirements_set(actor=mission.created_by, mission=mission, items=[
            {"skill_id": skill.id, "min_proficiency": 5, "required_count": 1},
            {"skill_id": skill.id, "min_proficiency": 5, "required_count": 3},
        ])


def test_requirements_reject_other_tenants_skill():
    mission = MissionFactory()
    set_current_tenant_id(mission.tenant_id)
    foreign_skill = SkillFactory()  # different tenant
    with pytest.raises(ApplicationError) as exc:
        mission_requirements_set(actor=mission.created_by, mission=mission, items=[
            {"skill_id": foreign_skill.id, "min_proficiency": 5, "required_count": 1},
        ])
    assert exc.value.extra == {"skill_ids": [foreign_skill.id]}


def test_requirements_reject_out_of_range_proficiency():
    mission = MissionFactory()
    set_current_tenant_id(mission.tenant_id)
    skill = SkillFactory(tenant=mission.tenant)
    with pytest.raises(ValidationError):
        mission_requirements_set(actor=mission.created_by, mission=mission, items=[
            {"skill_id": skill.id, "min_proficiency": 11, "required_count": 1},
        ])
    assert not MissionRequirement.objects.filter(mission=mission).exists()


def test_requirements_locked_outside_draft_or_rejected():
    mission = MissionFactory(status=MissionStatus.APPROVED)
    set_current_tenant_id(mission.tenant_id)
    skill = SkillFactory(tenant=mission.tenant)
    with pytest.raises(ApplicationError):
        mission_requirements_set(actor=mission.created_by, mission=mission, items=[
            {"skill_id": skill.id, "min_proficiency": 5, "required_count": 1},
        ])


def test_requirements_ownership_enforced():
    mission = MissionFactory()
    set_current_tenant_id(mission.tenant_id)
    other_lead = UserFactory(role=Role.MISSION_LEAD, tenant=mission.tenant)
    skill = SkillFactory(tenant=mission.tenant)
    with pytest.raises(PermissionDenied):
        mission_requirements_set(actor=other_lead, mission=mission, items=[
            {"skill_id": skill.id, "min_proficiency": 5, "required_count": 1},
        ])


def test_requirements_set_empty_clears_all():
    mission = MissionFactory()
    set_current_tenant_id(mission.tenant_id)
    skill = SkillFactory(tenant=mission.tenant)
    mission_requirements_set(actor=mission.created_by, mission=mission, items=[
        {"skill_id": skill.id, "min_proficiency": 5, "required_count": 1},
    ])
    mission_requirements_set(actor=mission.created_by, mission=mission, items=[])
    assert not MissionRequirement.objects.filter(mission=mission).exists()


# --- selectors ---------------------------------------------------------------------


def test_mission_list_is_tenant_scoped_and_newest_first():
    mission = MissionFactory(name="First")
    set_current_tenant_id(mission.tenant_id)
    newer = MissionFactory(tenant=mission.tenant, name="Second")
    MissionFactory(name="Other tenant")
    assert [m.name for m in mission_list()] == [newer.name, mission.name]


def test_mission_list_filters_by_status_and_search():
    mission = MissionFactory(name="Ganymede Survey")
    set_current_tenant_id(mission.tenant_id)
    MissionFactory(tenant=mission.tenant, name="Titan Descent", status=MissionStatus.ACTIVE)
    assert [m.name for m in mission_list(status=MissionStatus.ACTIVE)] == ["Titan Descent"]
    assert [m.name for m in mission_list(search="ganymede")] == ["Ganymede Survey"]


def test_mission_get_cross_tenant_raises_404():
    mine = MissionFactory()
    other = MissionFactory()
    set_current_tenant_id(mine.tenant_id)
    assert mission_get(mine.id).id == mine.id
    with pytest.raises(Http404):
        mission_get(other.id)


def test_mission_submitter_id_without_submission_is_none():
    mission = MissionFactory()
    set_current_tenant_id(mission.tenant_id)
    assert mission_submitter_id(mission) is None


def test_mission_submitter_id_tracks_the_latest_submission():
    mission = MissionFactory()
    MissionRequirementFactory(mission=mission)
    set_current_tenant_id(mission.tenant_id)
    director = UserFactory(role=Role.DIRECTOR, tenant=mission.tenant)

    transition_mission(actor=mission.created_by, mission=mission, action="submit")
    assert mission_submitter_id(mission) == mission.created_by_id
    transition_mission(actor=director, mission=mission, action="reject", reason="No")
    transition_mission(actor=mission.created_by, mission=mission, action="revise")
    transition_mission(actor=director, mission=mission, action="submit")
    assert mission_submitter_id(mission) == director.id
