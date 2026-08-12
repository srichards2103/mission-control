from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from mission_control.common.exceptions import ApplicationError
from mission_control.missions.models import (
    Mission,
    MissionRequirement,
    MissionStatus,
    MissionTransition,
)
from mission_control.missions.selectors.missions import mission_submitter_id
from mission_control.tenants.context import require_current_tenant_id
from mission_control.users.models import Skill
from mission_control.users.permissions import Permission, ensure_permission
from mission_control.users.roles import Role

S = MissionStatus


@dataclass(frozen=True)
class Transition:
    from_statuses: frozenset[str]
    to_status: str
    permission: Permission
    requires_reason: bool = False


# The mission lifecycle, exactly as specified. Read it against spec §8:
# every legal (action, from-state -> to-state, permission, reason?) row lives here and
# nowhere else -- anything absent from this table is an illegal transition.
TRANSITIONS: dict[str, Transition] = {
    "submit": Transition(frozenset({S.DRAFT}), S.PENDING_APPROVAL, Permission.MISSION_PROGRESS),
    "approve": Transition(frozenset({S.PENDING_APPROVAL}), S.APPROVED, Permission.MISSION_REVIEW),
    "reject": Transition(
        frozenset({S.PENDING_APPROVAL}), S.REJECTED, Permission.MISSION_REVIEW, True
    ),
    "revise": Transition(frozenset({S.REJECTED}), S.DRAFT, Permission.MISSION_PROGRESS),
    "activate": Transition(frozenset({S.APPROVED}), S.ACTIVE, Permission.MISSION_PROGRESS),
    "complete": Transition(frozenset({S.ACTIVE}), S.COMPLETED, Permission.MISSION_PROGRESS),
    "cancel": Transition(
        # Any non-terminal state; COMPLETED and CANCELLED are the terminal ones.
        frozenset({S.DRAFT, S.PENDING_APPROVAL, S.APPROVED, S.REJECTED, S.ACTIVE}),
        S.CANCELLED,
        Permission.MISSION_PROGRESS,
        True,
    ),
}

EDITABLE_STATUSES = frozenset({S.DRAFT, S.REJECTED})


def _ensure_owns_or_director(actor, mission: Mission) -> None:
    if actor.role != Role.DIRECTOR and mission.created_by_id != actor.id:
        raise PermissionDenied("You can only manage missions you created.")


def _ensure_not_reviewing_own_mission(actor, mission: Mission) -> None:
    """No self-approval: neither the mission's creator nor its latest submitter may review it.

    Directors are not exempt -- a director who raised or submitted the mission still needs
    a second pair of eyes.
    """
    if actor.id in {mission.created_by_id, mission_submitter_id(mission)}:
        raise PermissionDenied("You cannot review your own mission.")


def _lock_accepted_crew(mission: Mission) -> None:
    """Row-lock the mission's accepted crew's `User` rows, in a deterministic order.

    Serializes competing approvals/activations that share crew members: whichever
    transition gets here first holds the lock until its transaction commits, so the
    second one to run sees the first one's committed state (e.g. a hard-block conflict
    it just created) rather than a stale read from before it started.

    Sourced from `accepted_assignments` -- the Task 4.2 selectors' one definition of
    "this mission's accepted crew" (accepted assignment + `user__is_active=True`) --
    rather than re-deriving it here, so this can never quietly diverge from what
    `mission_coverage`/`staffing_validation_errors` count. `User` does not inherit
    `TenantModel` and `User.objects` is not tenant-scoped (see project constraints), so
    the explicit `tenant_id` filter is load-bearing, matching the precedent in
    `services/assignments.py`.

    `.order_by("id")` is not decoration: Postgres locks rows in scan order, and without
    a fixed order two transactions approving/activating missions that share two or more
    crew members could acquire the same `User` rows in opposite orders and deadlock --
    the loser's `DeadlockDetected` is neither an `ApplicationError` nor a DRF exception,
    so it would surface as an unhandled 500. `LockRows` sits above `Sort` in the query
    plan, so ordering the queryset here is sufficient to fix the lock order.
    """
    from mission_control.missions.selectors.staffing import accepted_assignments
    from mission_control.users.models import User

    accepted_user_ids = list(accepted_assignments(mission).values_list("user_id", flat=True))
    list(
        User.objects.select_for_update()
        .filter(id__in=accepted_user_ids, tenant_id=mission.tenant_id)
        .order_by("id")
    )


def _validate_staffing_for_approval(mission: Mission) -> None:
    """Full staffing validation for the approve guard: coverage, crew bounds, conflicts.

    This is the only place `approve` checks staffing; spec §8 lists "staffing valid"
    as approve's guard.
    """
    from mission_control.missions.selectors.staffing import staffing_validation_errors

    _lock_accepted_crew(mission)
    errors = staffing_validation_errors(mission)
    if errors:
        raise ApplicationError("Mission staffing is not valid.", extra={"errors": errors})


def _validate_conflicts_for_activation(mission: Mission) -> None:
    """Belt-and-braces re-check for the activate guard: conflicts only, not full validation.

    Spec §8 describes activate's staffing check as "re-runs conflict check (belt and
    braces)" -- narrower than approve's full "staffing valid". Coverage/crew-bounds
    proven at approve time CAN regress before activation -- via `assignment_remove` (a
    lead/director action, independent of this FSM) flipping an accepted assignment to
    `removed`, or via a crew member being deactivated, which drops them out of
    `accepted_assignments` per the Task 4.2 ruling that deactivated crew stop
    filling seats -- and re-running the full validation here would block activation of
    an already-approved mission over exactly that kind of change, which the plan does
    not intend. What CAN'T be caught any other way, and so is the one thing this
    re-check exists for, is a *different* mission getting approved in the meantime and
    hard-blocking one of this mission's accepted crew.
    """
    from mission_control.missions.selectors.staffing import mission_conflict_errors

    _lock_accepted_crew(mission)
    errors = mission_conflict_errors(mission)
    if errors:
        raise ApplicationError("Mission staffing is not valid.", extra={"errors": errors})


def _run_guards(action: str, mission: Mission) -> None:
    """Domain guards that go beyond the state table itself."""
    if action == "submit" and not mission.requirements.exists():
        raise ApplicationError("Add at least one skill requirement before submitting.")
    if action == "approve":
        _validate_staffing_for_approval(mission)
    # `timezone.localdate()`, not `dt.date.today()`: the FSM's date guards must run in
    # the project timezone (TIME_ZONE), not whatever the container happens to be set to.
    # `start_date`/`end_date` are DateFields that a user picked in the org's calendar,
    # and near midnight the two answers differ by a day.
    if action == "activate":
        if mission.start_date > timezone.localdate():
            raise ApplicationError("Mission cannot activate before its start date.")
        _validate_conflicts_for_activation(mission)
    if action == "complete" and mission.end_date > timezone.localdate():
        raise ApplicationError("Mission cannot complete before its end date.")


@transaction.atomic
def transition_mission(
    *, actor, mission: Mission, action: str, reason: str | None = None
) -> Mission:
    """Move a mission through the lifecycle, writing an audit row in the same transaction."""
    spec = TRANSITIONS.get(action)
    if spec is None:
        raise ApplicationError(f"Unknown action '{action}'.")

    ensure_permission(actor, spec.permission)
    # Re-read under a row lock so concurrent transitions serialise on the current status.
    mission = Mission.objects.select_for_update().get(id=mission.id)

    if spec.permission == Permission.MISSION_PROGRESS:
        # Progress actions are the lead's own: leads move their missions, directors move any.
        _ensure_owns_or_director(actor, mission)
    if spec.permission == Permission.MISSION_REVIEW:
        # Review actions (approve/reject) are the second pair of eyes.
        _ensure_not_reviewing_own_mission(actor, mission)

    if mission.status not in spec.from_statuses:
        raise ApplicationError(f"Cannot {action} a mission in state '{mission.status}'.")
    if spec.requires_reason and not (reason or "").strip():
        raise ApplicationError(f"A reason is required to {action}.")
    _run_guards(action, mission)

    from_status = mission.status
    mission.status = spec.to_status
    mission.save(update_fields=["status", "updated_at"])
    MissionTransition.objects.create(
        mission=mission,
        from_status=from_status,
        to_status=spec.to_status,
        actor=actor,
        reason=reason or "",
    )
    if action == "cancel":
        # Same atomic transaction as the status write and audit row above: a cancel
        # that flips status but leaves crew assigned (or vice versa) is a defect.
        # `assignment_live_uniq` is a partial unique index on live statuses only, so
        # flipping these rows out of the live set can never collide with anything.
        from mission_control.missions.models import (
            LIVE_ASSIGNMENT_STATUSES,
            Assignment,
            AssignmentStatus,
        )

        Assignment.objects.filter(mission=mission, status__in=LIVE_ASSIGNMENT_STATUSES).update(
            status=AssignmentStatus.REMOVED
        )
    return mission


def mission_create(
    *, actor, name, description, start_date, end_date, min_crew, max_crew
) -> Mission:
    mission = Mission(
        name=name,
        description=description,
        start_date=start_date,
        end_date=end_date,
        min_crew=min_crew,
        max_crew=max_crew,
        created_by=actor,
    )
    # Tenant is stamped by TenantModel.save(); excluding it here keeps full_clean from
    # failing on the not-yet-set FK while still validating the date and crew-bound checks,
    # so those surface as the 400 validation envelope rather than an IntegrityError 500.
    mission.full_clean(exclude={"tenant"})
    mission.save()
    return mission


def mission_update(*, actor, mission: Mission, **fields) -> Mission:
    _ensure_owns_or_director(actor, mission)
    if mission.status not in EDITABLE_STATUSES:
        raise ApplicationError("Mission can only be edited in draft or rejected state.")
    for attr in ("name", "description", "start_date", "end_date", "min_crew", "max_crew"):
        if attr in fields:
            setattr(mission, attr, fields[attr])
    mission.full_clean(exclude={"tenant"})
    mission.save()
    return mission


@transaction.atomic
def mission_requirements_set(*, actor, mission: Mission, items: list[dict]) -> None:
    _ensure_owns_or_director(actor, mission)
    if mission.status not in EDITABLE_STATUSES:
        raise ApplicationError("Requirements can only be edited in draft or rejected state.")

    pairs = [(item["skill_id"], item["min_proficiency"]) for item in items]
    if len(pairs) != len(set(pairs)):
        raise ApplicationError("Duplicate skill/proficiency requirement rows.")

    skill_ids = {item["skill_id"] for item in items}
    # Tenant-scoped manager: another tenant's skill is simply unknown here.
    valid_ids = set(
        Skill.objects.filter(id__in=skill_ids, is_archived=False).values_list("id", flat=True)
    )
    missing = skill_ids - valid_ids
    if missing:
        raise ApplicationError("Unknown or archived skills.", extra={"skill_ids": sorted(missing)})

    rows = [
        MissionRequirement(
            tenant_id=require_current_tenant_id(),
            mission=mission,
            skill_id=item["skill_id"],
            min_proficiency=item["min_proficiency"],
            required_count=item["required_count"],
        )
        for item in items
    ]
    for row in rows:
        # bulk_create skips model validation, so validate the proficiency/count checks
        # here: they must come back as the 400 validation envelope, not an IntegrityError.
        # FKs are excluded (already verified above) and uniqueness is enforced by the
        # in-Python pair check plus the DB constraint.
        row.full_clean(exclude={"tenant", "mission", "skill"}, validate_unique=False)

    mission.requirements.all().delete()
    MissionRequirement.objects.bulk_create(rows)
