from django.db.models import QuerySet
from django.shortcuts import get_object_or_404

from mission_control.missions.models import (
    LIVE_ASSIGNMENT_STATUSES,
    Assignment,
    Mission,
    MissionStatus,
    MissionTransition,
)


def mission_list(*, status: str | None = None, search: str | None = None) -> QuerySet[Mission]:
    # `-id` only breaks ties on identical timestamps, keeping the order deterministic.
    qs = Mission.objects.select_related("created_by").order_by("-created_at", "-id")
    if status:
        qs = qs.filter(status=status)
    if search:
        qs = qs.filter(name__icontains=search)
    return qs


def mission_get(mission_id: int) -> Mission:
    qs = Mission.objects.select_related("created_by").prefetch_related(
        "requirements__skill", "transitions__actor"
    )
    # The manager is tenant-scoped, so another tenant's mission is a 404, never a 403.
    return get_object_or_404(qs, id=mission_id)


def mission_submitter_id(mission: Mission) -> int | None:
    """The actor of the mission's most recent submission, or None if it was never submitted.

    A mission can be submitted, rejected and re-submitted, so only the latest
    `-> pending_approval` row identifies the person awaiting a decision. `-id` breaks
    ties in case two rows share a timestamp.
    """
    return (
        MissionTransition.objects.filter(
            mission=mission, to_status=MissionStatus.PENDING_APPROVAL
        )
        .order_by("-created_at", "-id")
        .values_list("actor_id", flat=True)
        .first()
    )


def my_assignments(user) -> QuerySet[Assignment]:
    """A crew member's own assignments, newest first, for `/me/assignments/`."""
    return Assignment.objects.filter(user=user).select_related("mission").order_by("-created_at")


def mission_assignments(mission: Mission) -> QuerySet[Assignment]:
    """A mission's live (proposed/accepted) assignments -- the staffing roster."""
    return (
        Assignment.objects.filter(mission=mission, status__in=LIVE_ASSIGNMENT_STATUSES)
        .select_related("user")
        .order_by("-created_at")
    )
