"""Assignment writes: propose, remove, respond.

All three staffing questions (hard block, soft conflict, coverage) are answered by
Task 4.2's selectors in `missions.selectors.staffing` -- this module never re-derives a
date-overlap or status predicate itself; see `hard_blocked_user_ids` below.
"""

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from mission_control.common.db import integrity_error_as
from mission_control.common.exceptions import ApplicationError
from mission_control.missions.models import (
    LIVE_ASSIGNMENT_STATUSES,
    Assignment,
    AssignmentStatus,
    Mission,
    MissionStatus,
)
from mission_control.missions.selectors.staffing import hard_blocked_user_ids
from mission_control.missions.services.missions import _ensure_owns_or_director
from mission_control.tenants.context import require_current_tenant_id
from mission_control.users.models import User
from mission_control.users.roles import Role

TERMINAL = frozenset({MissionStatus.COMPLETED, MissionStatus.CANCELLED})


@transaction.atomic
def assignments_propose(*, actor, mission: Mission, user_ids: list[int]) -> list[Assignment]:
    _ensure_owns_or_director(actor, mission)
    if mission.status in TERMINAL:
        raise ApplicationError("Cannot assign crew to a completed or cancelled mission.")

    unique_ids = set(user_ids)
    tenant_id = require_current_tenant_id()
    # User does not inherit TenantModel (see project constraints), so the tenant filter
    # here is load-bearing, not decorative -- User.objects is not tenant-scoped.
    users = list(
        User.objects.filter(
            id__in=unique_ids, tenant_id=tenant_id, role=Role.CREW_MEMBER, is_active=True
        )
    )
    if len(users) != len(unique_ids):
        missing = unique_ids - {u.id for u in users}
        raise ApplicationError(
            "Some users are not assignable crew members.", extra={"user_ids": sorted(missing)}
        )

    already = set(
        Assignment.objects.filter(
            mission=mission, user_id__in=unique_ids, status__in=LIVE_ASSIGNMENT_STATUSES
        ).values_list("user_id", flat=True)
    )
    if already:
        names = ", ".join(sorted(u.name for u in users if u.id in already))
        raise ApplicationError(
            f"Already assigned to this mission: {names}.", extra={"user_ids": sorted(already)}
        )

    # exclude_mission_id=mission.id: without it, this mission's own accepted crew (if
    # any are already accepted here and this range is itself approved/active) would
    # come back hard-blocked by themselves.
    blocked = hard_blocked_user_ids(
        start_date=mission.start_date, end_date=mission.end_date, exclude_mission_id=mission.id
    ) & unique_ids
    if blocked:
        names = ", ".join(sorted(u.name for u in users if u.id in blocked))
        raise ApplicationError(
            f"Unavailable for these dates: {names}.", extra={"user_ids": sorted(blocked)}
        )

    live_count = Assignment.objects.filter(
        mission=mission, status__in=LIVE_ASSIGNMENT_STATUSES
    ).count()
    if live_count + len(users) > mission.max_crew:
        raise ApplicationError(f"This would exceed max_crew ({mission.max_crew}).")

    created = []
    for user in users:
        assignment = Assignment(tenant_id=tenant_id, mission=mission, user=user, created_by=actor)
        # See `integrity_error_as`: the `already` pre-check above and full_clean()'s
        # validate_constraints() below are both non-locking SELECTs, so a concurrent
        # proposal for this same (mission, user) can slip past both and lose the race at
        # the INSERT. The helper's savepoint also keeps that failure from poisoning this
        # function's own @transaction.atomic mid-loop.
        with integrity_error_as(f"{user.name} was just assigned to this mission by someone else."):
            # full_clean() (not bulk_create, which skips validation) so the ordinary
            # case -- no concurrent writer -- surfaces the partial
            # `assignment_live_uniq` constraint as a clean 400 validation envelope.
            assignment.full_clean()
            assignment.save()
        created.append(assignment)
    return created


def assignment_remove(*, actor, assignment: Assignment) -> Assignment:
    _ensure_owns_or_director(actor, assignment.mission)
    if assignment.status not in LIVE_ASSIGNMENT_STATUSES:
        raise ApplicationError("Only proposed or accepted assignments can be removed.")
    assignment.status = AssignmentStatus.REMOVED
    assignment.save(update_fields=["status", "updated_at"])
    return assignment


def assignment_respond(
    *, actor, assignment: Assignment, action: str, reason: str = ""
) -> Assignment:
    if assignment.user_id != actor.id:
        raise PermissionDenied("You can only respond to your own assignments.")
    if assignment.mission.status in TERMINAL:
        raise ApplicationError("This mission is no longer active.")
    if assignment.status != AssignmentStatus.PROPOSED:
        raise ApplicationError("This assignment has already been responded to.")
    if action == "accept":
        # Availability is re-checked HERE, not only at propose time: a proposal can be
        # outstanding for arbitrarily long, and in the meantime a *different* mission
        # this crew member already accepted can be approved, hard-blocking them. The
        # propose-time check would then be stale, and accepting would manufacture the
        # one state the rest of the system assumes impossible -- two accepted
        # assignments on overlapping approved/active missions (spec §9's "first-approved
        # wins the reservation"). Same single-source predicate as propose, with the same
        # `exclude_mission_id` reasoning: this mission's own crew must not block itself.
        blocked = hard_blocked_user_ids(
            start_date=assignment.mission.start_date,
            end_date=assignment.mission.end_date,
            exclude_mission_id=assignment.mission_id,
        )
        if actor.id in blocked:
            raise ApplicationError("You are already committed to an overlapping mission.")
        assignment.status = AssignmentStatus.ACCEPTED
    elif action == "decline":
        assignment.status = AssignmentStatus.DECLINED
        assignment.decline_reason = reason
    else:
        raise ApplicationError(f"Unknown action '{action}'.")
    assignment.responded_at = timezone.now()
    assignment.save(update_fields=["status", "decline_reason", "responded_at", "updated_at"])
    return assignment
