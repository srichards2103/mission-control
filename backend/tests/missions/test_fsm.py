import datetime as dt

import pytest
from rest_framework.exceptions import PermissionDenied

from mission_control.common.exceptions import ApplicationError
from mission_control.missions.factories import MissionFactory, MissionRequirementFactory
from mission_control.missions.models import Mission, MissionStatus, MissionTransition
from mission_control.missions.services.missions import TRANSITIONS, transition_mission
from mission_control.tenants.context import set_current_tenant_id
from mission_control.users.factories import UserFactory
from mission_control.users.roles import Role

pytestmark = pytest.mark.django_db


@pytest.fixture
def mission_with_requirement():
    mission = MissionFactory()
    MissionRequirementFactory(mission=mission)
    set_current_tenant_id(mission.tenant_id)
    return mission


def director_for(mission):
    return UserFactory(role=Role.DIRECTOR, tenant=mission.tenant)


def force_status(mission, status):
    """Put a mission into `status` without going through the FSM (test setup only)."""
    Mission.objects.filter(id=mission.id).update(status=status)
    mission.status = status
    return mission


# --- Brief scenarios ---------------------------------------------------------------


def test_happy_path_submit_approve(mission_with_requirement):
    mission = mission_with_requirement
    lead = mission.created_by
    mission = transition_mission(actor=lead, mission=mission, action="submit")
    assert mission.status == MissionStatus.PENDING_APPROVAL
    mission = transition_mission(actor=director_for(mission), mission=mission, action="approve")
    assert mission.status == MissionStatus.APPROVED
    assert mission.transitions.count() == 2


def test_submit_requires_a_requirement():
    mission = MissionFactory()
    set_current_tenant_id(mission.tenant_id)
    with pytest.raises(ApplicationError, match="requirement"):
        transition_mission(actor=mission.created_by, mission=mission, action="submit")


def test_creator_director_cannot_approve_own():
    director = UserFactory(role=Role.DIRECTOR)
    mission = MissionFactory(tenant=director.tenant, created_by=director)
    MissionRequirementFactory(mission=mission)
    set_current_tenant_id(mission.tenant_id)
    transition_mission(actor=director, mission=mission, action="submit")
    with pytest.raises(PermissionDenied):
        transition_mission(actor=director, mission=mission, action="approve")


def test_submitter_cannot_approve(mission_with_requirement):
    mission = mission_with_requirement
    submitting_director = director_for(mission)
    transition_mission(actor=submitting_director, mission=mission, action="submit")
    with pytest.raises(PermissionDenied):
        transition_mission(actor=submitting_director, mission=mission, action="approve")


def test_reject_requires_reason(mission_with_requirement):
    mission = mission_with_requirement
    transition_mission(actor=mission.created_by, mission=mission, action="submit")
    with pytest.raises(ApplicationError, match="reason"):
        transition_mission(actor=director_for(mission), mission=mission, action="reject")


def test_reject_then_revise_reopens_draft(mission_with_requirement):
    mission = mission_with_requirement
    transition_mission(actor=mission.created_by, mission=mission, action="submit")
    mission = transition_mission(
        actor=director_for(mission), mission=mission, action="reject", reason="Not enough detail"
    )
    assert mission.status == MissionStatus.REJECTED
    mission = transition_mission(actor=mission.created_by, mission=mission, action="revise")
    assert mission.status == MissionStatus.DRAFT


def test_lead_cannot_progress_others_mission(mission_with_requirement):
    mission = mission_with_requirement
    other_lead = UserFactory(role=Role.MISSION_LEAD, tenant=mission.tenant)
    with pytest.raises(PermissionDenied):
        transition_mission(actor=other_lead, mission=mission, action="submit")


def test_crew_cannot_transition(mission_with_requirement):
    mission = mission_with_requirement
    crew = UserFactory(role=Role.CREW_MEMBER, tenant=mission.tenant)
    with pytest.raises(PermissionDenied):
        transition_mission(actor=crew, mission=mission, action="submit")


def test_activate_needs_start_date_reached(mission_with_requirement):
    mission = mission_with_requirement  # factory default: starts 10 days in the future
    transition_mission(actor=mission.created_by, mission=mission, action="submit")
    mission = transition_mission(actor=director_for(mission), mission=mission, action="approve")
    with pytest.raises(ApplicationError, match="start date"):
        transition_mission(actor=mission.created_by, mission=mission, action="activate")


def test_invalid_state_transition(mission_with_requirement):
    mission = mission_with_requirement
    with pytest.raises(ApplicationError, match="Cannot approve"):
        transition_mission(actor=director_for(mission), mission=mission, action="approve")


def test_cancel_from_terminal_forbidden(mission_with_requirement):
    mission = mission_with_requirement
    mission = transition_mission(
        actor=mission.created_by, mission=mission, action="cancel", reason="Scrapped"
    )
    assert mission.status == MissionStatus.CANCELLED
    with pytest.raises(ApplicationError):
        transition_mission(
            actor=mission.created_by, mission=mission, action="cancel", reason="Again"
        )


# --- The rest of the table ---------------------------------------------------------


def test_full_lifecycle_to_completed():
    today = dt.date.today()
    mission = MissionFactory(start_date=today - dt.timedelta(days=5), end_date=today)
    MissionRequirementFactory(mission=mission)
    set_current_tenant_id(mission.tenant_id)
    lead, director = mission.created_by, director_for(mission)

    mission = transition_mission(actor=lead, mission=mission, action="submit")
    mission = transition_mission(actor=director, mission=mission, action="approve")
    mission = transition_mission(actor=lead, mission=mission, action="activate")
    assert mission.status == MissionStatus.ACTIVE
    mission = transition_mission(actor=lead, mission=mission, action="complete")
    assert mission.status == MissionStatus.COMPLETED
    assert [t.to_status for t in mission.transitions.order_by("created_at", "id")] == [
        MissionStatus.PENDING_APPROVAL,
        MissionStatus.APPROVED,
        MissionStatus.ACTIVE,
        MissionStatus.COMPLETED,
    ]


def test_complete_needs_end_date_reached(mission_with_requirement):
    mission = force_status(mission_with_requirement, MissionStatus.ACTIVE)
    with pytest.raises(ApplicationError, match="end date"):
        transition_mission(actor=mission.created_by, mission=mission, action="complete")


def test_director_may_progress_another_leads_mission(mission_with_requirement):
    mission = mission_with_requirement
    mission = transition_mission(actor=director_for(mission), mission=mission, action="submit")
    assert mission.status == MissionStatus.PENDING_APPROVAL


def test_unknown_action_rejected(mission_with_requirement):
    with pytest.raises(ApplicationError, match="Unknown action"):
        transition_mission(
            actor=mission_with_requirement.created_by,
            mission=mission_with_requirement,
            action="teleport",
        )


ILLEGAL_PAIRS = [
    (action, status)
    for action, spec in TRANSITIONS.items()
    for status in MissionStatus.values
    if status not in spec.from_statuses
]


@pytest.mark.parametrize(("action", "status"), ILLEGAL_PAIRS)
def test_illegal_transitions_are_rejected(mission_with_requirement, action, status):
    """Every (action, from-state) pair the table does not permit is a business-rule error."""
    mission = force_status(mission_with_requirement, status)
    director = director_for(mission)
    with pytest.raises(ApplicationError, match=f"Cannot {action}"):
        transition_mission(actor=director, mission=mission, action=action, reason="Because")
    assert Mission.objects.get(id=mission.id).status == status
    assert not MissionTransition.objects.filter(mission=mission).exists()


# --- Audit trail -------------------------------------------------------------------


def test_transition_writes_audit_row(mission_with_requirement):
    mission = mission_with_requirement
    transition_mission(actor=mission.created_by, mission=mission, action="submit")
    director = director_for(mission)
    transition_mission(actor=director, mission=mission, action="reject", reason="Too vague")

    row = MissionTransition.objects.filter(mission=mission).first()  # Meta.ordering: newest first
    assert (row.from_status, row.to_status) == (
        MissionStatus.PENDING_APPROVAL,
        MissionStatus.REJECTED,
    )
    assert row.actor_id == director.id
    assert row.reason == "Too vague"
    assert row.tenant_id == mission.tenant_id


def test_transition_without_reason_stores_empty_string(mission_with_requirement):
    mission = mission_with_requirement
    transition_mission(actor=mission.created_by, mission=mission, action="submit")
    assert MissionTransition.objects.filter(mission=mission).first().reason == ""


def test_status_change_and_audit_row_are_atomic(mission_with_requirement, monkeypatch):
    """If the audit row cannot be written, the status change must roll back with it."""
    mission = mission_with_requirement

    def boom(*args, **kwargs):
        raise RuntimeError("audit write failed")

    monkeypatch.setattr(MissionTransition.objects, "create", boom)
    with pytest.raises(RuntimeError):
        transition_mission(actor=mission.created_by, mission=mission, action="submit")

    assert Mission.objects.get(id=mission.id).status == MissionStatus.DRAFT
    monkeypatch.undo()
    assert not MissionTransition.objects.filter(mission=mission).exists()


def test_failed_guard_leaves_no_trace(mission_with_requirement):
    mission = mission_with_requirement
    transition_mission(actor=mission.created_by, mission=mission, action="submit")
    with pytest.raises(ApplicationError):
        transition_mission(actor=director_for(mission), mission=mission, action="reject")

    assert Mission.objects.get(id=mission.id).status == MissionStatus.PENDING_APPROVAL
    assert MissionTransition.objects.filter(mission=mission).count() == 1


# --- Self-review block: submitter derivation ---------------------------------------


def test_approver_may_be_a_director_who_never_touched_the_mission(mission_with_requirement):
    mission = mission_with_requirement
    transition_mission(actor=mission.created_by, mission=mission, action="submit")
    mission = transition_mission(actor=director_for(mission), mission=mission, action="approve")
    assert mission.status == MissionStatus.APPROVED


def test_no_submission_row_does_not_block_approval(mission_with_requirement):
    """A mission parked in pending_approval with no audit history has no submitter."""
    mission = force_status(mission_with_requirement, MissionStatus.PENDING_APPROVAL)
    mission = transition_mission(actor=director_for(mission), mission=mission, action="approve")
    assert mission.status == MissionStatus.APPROVED


def test_only_the_latest_submitter_is_blocked(mission_with_requirement):
    """After a reject/revise/re-submit cycle, the *first* submitter may review again."""
    mission = mission_with_requirement
    first_submitter = director_for(mission)
    second_reviewer = director_for(mission)

    transition_mission(actor=first_submitter, mission=mission, action="submit")
    mission = transition_mission(
        actor=second_reviewer, mission=mission, action="reject", reason="Needs work"
    )
    mission = transition_mission(actor=mission.created_by, mission=mission, action="revise")
    mission = transition_mission(actor=second_reviewer, mission=mission, action="submit")

    with pytest.raises(PermissionDenied):
        transition_mission(actor=second_reviewer, mission=mission, action="approve")
    mission = transition_mission(actor=first_submitter, mission=mission, action="approve")
    assert mission.status == MissionStatus.APPROVED


def test_creator_cannot_reject_own_mission(mission_with_requirement):
    """The no-self-review rule covers reject as well as approve, via the creator path."""
    mission = mission_with_requirement
    creator_promoted_to_director = mission.created_by
    creator_promoted_to_director.role = Role.DIRECTOR
    creator_promoted_to_director.save()
    transition_mission(actor=director_for(mission), mission=mission, action="submit")
    with pytest.raises(PermissionDenied):
        transition_mission(
            actor=creator_promoted_to_director, mission=mission, action="reject", reason="No"
        )
