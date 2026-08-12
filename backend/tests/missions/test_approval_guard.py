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


def staffed_approved_mission(**kwargs):
    """An already-approved, activatable mission (start date reached) with one accepted,
    qualified crew member -- the starting point for the activate-guard split tests.
    """
    today = dt.date.today()
    mission = MissionFactory(
        start_date=today - dt.timedelta(days=1),
        end_date=today + dt.timedelta(days=9),
        status=MissionStatus.APPROVED,
        **kwargs,
    )
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


# --- The approve/activate split (Finding 2: the deliverable of this task, pinned) --------


def test_activate_succeeds_despite_post_approval_coverage_loss():
    """The regression the controller ruling exists to prevent: coverage dropping after
    approval (here, the sole accepted crew member declining) must NOT block activation
    -- activate re-checks conflicts only, not the full staffing validation.
    """
    mission, crew = staffed_approved_mission()
    Assignment.objects.filter(user=crew).update(status=AssignmentStatus.DECLINED)
    result = transition_mission(actor=mission.created_by, mission=mission, action="activate")
    assert result.status == MissionStatus.ACTIVE


def test_activate_blocked_by_conflict_from_mission_approved_in_interim():
    """What activate's re-check DOES exist to catch: a different mission, holding the
    same crew member accepted with overlapping dates, reaching approved/active status
    after this mission was already approved.
    """
    mission, crew = staffed_approved_mission()
    competitor = MissionFactory(
        tenant=mission.tenant,
        status=MissionStatus.APPROVED,
        start_date=mission.start_date,
        end_date=mission.end_date,
    )
    AssignmentFactory(
        mission=competitor, user=crew, status=AssignmentStatus.ACCEPTED, tenant=mission.tenant
    )
    with pytest.raises(ApplicationError) as exc:
        transition_mission(actor=mission.created_by, mission=mission, action="activate")
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
    """Fault injection proving the strong direction: even a cascade `UPDATE` that has
    already taken effect (the assignment genuinely flips to `removed` inside the open
    transaction) rolls back along with the status change and audit row if something
    fails immediately afterward, still inside the same atomic block.

    Injecting the fault *before* `.update()` runs is the weaker version: it can't
    distinguish "the cascade never ran" from "the cascade ran and then correctly rolled
    back", because the assignment would read back as ACCEPTED either way. Letting the
    real `QuerySet.update()` execute first -- so the row is actually written to
    `removed` inside the transaction -- and then raising closes that gap: the
    post-rollback assertion below can only pass if the write was truly undone.
    """
    from django.db.models.query import QuerySet

    mission, crew = staffed_pending_mission()
    real_update = QuerySet.update

    def update_then_boom(self, **kwargs):
        real_update(self, **kwargs)
        raise RuntimeError("cascade write failed after taking effect")

    monkeypatch.setattr(QuerySet, "update", update_then_boom)
    with pytest.raises(RuntimeError):
        transition_mission(
            actor=mission.created_by, mission=mission, action="cancel", reason="Scrubbed"
        )
    monkeypatch.undo()

    mission.refresh_from_db()
    assert mission.status == MissionStatus.PENDING_APPROVAL
    assert not mission.transitions.exists()
    assert Assignment.objects.get(user=crew).status == AssignmentStatus.ACCEPTED
