import datetime as dt

import pytest

from mission_control.common.exceptions import ApplicationError
from mission_control.missions.factories import (
    AssignmentFactory,
    MissionFactory,
    MissionRequirementFactory,
)
from mission_control.missions.models import Assignment, AssignmentStatus, MissionStatus
from mission_control.missions.services.missions import transition_mission
from mission_control.tenants.context import set_current_tenant_id
from mission_control.users.factories import CrewSkillFactory, SkillFactory, UserFactory
from mission_control.users.roles import Role

pytestmark = pytest.mark.django_db
D = dt.date


def staffed_pending_mission(**kwargs):
    mission = MissionFactory(start_date=D(2026, 9, 1), end_date=D(2026, 9, 10),
                             status=MissionStatus.PENDING_APPROVAL, **kwargs)
    set_current_tenant_id(mission.tenant_id)
    skill = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=skill, min_proficiency=5)
    crew = UserFactory(role=Role.CREW_MEMBER, tenant=mission.tenant, name="Ada")
    CrewSkillFactory(user=crew, skill=skill, proficiency=8)
    AssignmentFactory(mission=mission, user=crew, status=AssignmentStatus.ACCEPTED)
    return mission, crew


def test_approve_succeeds_when_staffed():
    mission, _ = staffed_pending_mission()
    director = UserFactory(role=Role.DIRECTOR, tenant=mission.tenant)
    assert transition_mission(actor=director, mission=mission,
                              action="approve").status == MissionStatus.APPROVED


def test_approve_fails_without_coverage():
    mission, crew = staffed_pending_mission()
    Assignment.objects.filter(user=crew).update(status=AssignmentStatus.DECLINED)
    director = UserFactory(role=Role.DIRECTOR, tenant=mission.tenant)
    with pytest.raises(ApplicationError) as exc:
        transition_mission(actor=director, mission=mission, action="approve")
    assert "Piloting" in str(exc.value.extra["errors"])


def test_competing_approval_loses_shared_crew():
    mission_a, crew = staffed_pending_mission()
    director = UserFactory(role=Role.DIRECTOR, tenant=mission_a.tenant)
    # Mission B, same tenant, overlapping dates, same accepted crew member
    mission_b = MissionFactory(tenant=mission_a.tenant, status=MissionStatus.PENDING_APPROVAL,
                               start_date=D(2026, 9, 5), end_date=D(2026, 9, 15))
    skill_b = SkillFactory(tenant=mission_a.tenant, name="Navigation")
    MissionRequirementFactory(mission=mission_b, skill=skill_b, min_proficiency=1)
    CrewSkillFactory(user=crew, skill=skill_b, proficiency=5)
    AssignmentFactory(mission=mission_b, user=crew, status=AssignmentStatus.ACCEPTED)

    transition_mission(actor=director, mission=mission_a, action="approve")
    with pytest.raises(ApplicationError) as exc:
        transition_mission(actor=director, mission=mission_b, action="approve")
    assert "Ada" in str(exc.value.extra["errors"])


def test_cancel_removes_live_assignments():
    mission, crew = staffed_pending_mission()
    transition_mission(
        actor=mission.created_by, mission=mission, action="cancel", reason="Scrubbed"
    )
    assignment = Assignment.objects.get(user=crew)
    assert assignment.status == AssignmentStatus.REMOVED


def test_cancel_leaves_only_live_assignments_removed():
    """Declined/removed assignments are untouched; only proposed/accepted flip."""
    mission, crew = staffed_pending_mission()
    already_declined = AssignmentFactory(
        mission=mission, status=AssignmentStatus.DECLINED, tenant=mission.tenant
    )
    proposed = AssignmentFactory(
        mission=mission, status=AssignmentStatus.PROPOSED, tenant=mission.tenant
    )
    transition_mission(
        actor=mission.created_by, mission=mission, action="cancel", reason="Scrubbed"
    )
    assert Assignment.objects.get(user=crew).status == AssignmentStatus.REMOVED
    assert Assignment.objects.get(id=proposed.id).status == AssignmentStatus.REMOVED
    assert Assignment.objects.get(id=already_declined.id).status == AssignmentStatus.DECLINED


def test_cancel_cascade_is_atomic_with_status_change_and_audit_row(monkeypatch):
    """Fault injection: if the assignment cascade write blows up, the status change and
    the audit row it belongs to must roll back with it -- proving atomicity, not just
    asserting the happy path succeeded.
    """
    mission, crew = staffed_pending_mission()

    def boom(*args, **kwargs):
        raise RuntimeError("cascade write failed")

    # `Assignment.objects` is a cached manager instance shared by every access, so
    # patching `.filter` here intercepts exactly the cascade's
    # `Assignment.objects.filter(...).update(...)` call inside `transition_mission`.
    monkeypatch.setattr(Assignment.objects, "filter", boom)
    with pytest.raises(RuntimeError):
        transition_mission(
            actor=mission.created_by, mission=mission, action="cancel", reason="Scrubbed"
        )
    monkeypatch.undo()

    mission.refresh_from_db()
    assert mission.status == MissionStatus.PENDING_APPROVAL
    assert not mission.transitions.exists()
    assert Assignment.objects.get(user=crew).status == AssignmentStatus.ACCEPTED
