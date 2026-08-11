import pytest
from rest_framework.exceptions import PermissionDenied

from mission_control.users.factories import UserFactory
from mission_control.users.permissions import Permission, ensure_permission, permissions_for_role
from mission_control.users.roles import Role


def test_director_has_everything_except_crew_self_service():
    perms = permissions_for_role(Role.DIRECTOR)
    assert Permission.MISSION_REVIEW in perms
    assert Permission.SETTINGS_MANAGE in perms
    assert Permission.ASSIGNMENT_RESPOND not in perms
    assert Permission.OWN_SKILLS_EDIT not in perms
    assert len(perms) == 14


def test_mission_lead_set_exact():
    assert permissions_for_role(Role.MISSION_LEAD) == frozenset({
        Permission.MISSION_VIEW, Permission.MISSION_CREATE, Permission.MISSION_EDIT,
        Permission.MISSION_PROGRESS, Permission.ASSIGNMENT_MANAGE, Permission.MATCH_RUN,
        Permission.CREW_VIEW, Permission.SKILL_VIEW, Permission.DASHBOARD_VIEW,
    })


def test_crew_member_set_exact():
    assert permissions_for_role(Role.CREW_MEMBER) == frozenset({
        Permission.SKILL_VIEW, Permission.OWN_SKILLS_EDIT, Permission.ASSIGNMENT_RESPOND,
    })


@pytest.mark.django_db
def test_ensure_permission_raises_for_missing():
    crew = UserFactory(role=Role.CREW_MEMBER)
    ensure_permission(crew, Permission.OWN_SKILLS_EDIT)  # no raise
    with pytest.raises(PermissionDenied):
        ensure_permission(crew, Permission.MISSION_CREATE)
