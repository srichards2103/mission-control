"""Availability and coverage — the single source of truth for the scheduling rule.

> A crew member is **hard-blocked** for a date range iff they hold an *accepted*
> assignment on an *approved or active* mission whose dates overlap it. Any other
> overlap is a **soft conflict** — permitted, surfaced as a warning.

Every consumer (approve guard, matcher, dashboard, staffing panel) calls into this
module rather than re-deriving the predicate, so `_hard_block_qs` and `_overlapping`
below are the only places the rule is expressed.

Two deliberate narrowings of the prose, both settled and not bugs:

* An assignment on a `completed` or `cancelled` mission yields no soft conflict, even
  though spec §9's wording says "proposed anywhere" — §9's own enumeration of soft
  conflicts is a closed list of draft/pending/rejected. A finished or abandoned mission
  cannot compete for anyone's time.
* Seat filling ignores deactivated members (see `_accepted_assignments_qs`); the
  hard-block predicate itself does not, because the global availability rule is stated
  purely in terms of assignment status, mission status and dates.
"""

import datetime as dt
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field

from django.db.models import QuerySet

from mission_control.missions.models import (
    LIVE_ASSIGNMENT_STATUSES,
    Assignment,
    AssignmentStatus,
    Mission,
    MissionStatus,
)
from mission_control.users.models import CrewSkill

HARD_BLOCK_MISSION_STATUSES = frozenset({MissionStatus.APPROVED, MissionStatus.ACTIVE})

# A finished or abandoned mission cannot conflict with anything: its dates may still
# overlap, but nobody is expected to show up for it.
IRRELEVANT_MISSION_STATUSES = frozenset({MissionStatus.COMPLETED, MissionStatus.CANCELLED})


def _overlapping(
    qs: QuerySet[Assignment], start_date: dt.date, end_date: dt.date
) -> QuerySet[Assignment]:
    """Assignments whose mission overlaps [start_date, end_date].

    Day granularity, inclusive on both ends: `a.start <= b.end AND b.start <= a.end`.
    Two missions that merely touch (one ends the day the other starts) DO overlap.
    An assignment has no dates of its own — its period is its mission's.
    """
    return qs.filter(mission__start_date__lte=end_date, mission__end_date__gte=start_date)


def _hard_block_qs(
    *, start_date: dt.date, end_date: dt.date, exclude_mission_id: int | None = None
) -> QuerySet[Assignment]:
    """The hard-block predicate: accepted AND mission approved/active AND dates overlap."""
    qs = Assignment.objects.filter(
        status=AssignmentStatus.ACCEPTED,
        mission__status__in=HARD_BLOCK_MISSION_STATUSES,
    )
    if exclude_mission_id is not None:
        qs = qs.exclude(mission_id=exclude_mission_id)
    return _overlapping(qs, start_date, end_date)


def hard_blocked_user_ids(
    *, start_date: dt.date, end_date: dt.date, exclude_mission_id: int | None = None
) -> set[int]:
    """Users unavailable for the range because they are already committed elsewhere.

    Pass `exclude_mission_id` whenever the range belongs to a mission you are staffing.
    Without it, an already-approved/active mission's own accepted crew come back as
    blocked — by themselves — because their assignment satisfies the predicate.
    """
    qs = _hard_block_qs(
        start_date=start_date, end_date=end_date, exclude_mission_id=exclude_mission_id
    )
    return set(qs.values_list("user_id", flat=True))


def soft_conflicts_for_users(
    *,
    user_ids: Iterable[int],
    start_date: dt.date,
    end_date: dt.date,
    exclude_mission_id: int | None,
) -> dict[int, list[dict]]:
    """Overlapping live commitments that do NOT hard-block, keyed by user id.

    Soft conflict = live (proposed or accepted) assignment on another still-relevant
    mission whose dates overlap, minus the hard blocks (which the caller handles
    separately). Defined by subtracting `_hard_block_qs` so the two can never drift.

    Users with no conflicts are ABSENT from the returned dict rather than mapped to an
    empty list — the common case returns `{}`. Callers must use `.get(user_id, [])`.
    """
    hard_block_ids = _hard_block_qs(
        start_date=start_date, end_date=end_date, exclude_mission_id=exclude_mission_id
    ).values("id")
    qs = Assignment.objects.filter(
        user_id__in=user_ids, status__in=LIVE_ASSIGNMENT_STATUSES
    ).exclude(mission__status__in=IRRELEVANT_MISSION_STATUSES)
    if exclude_mission_id is not None:
        qs = qs.exclude(mission_id=exclude_mission_id)
    qs = (
        _overlapping(qs, start_date, end_date)
        .exclude(id__in=hard_block_ids)
        .select_related("mission")
        .order_by("mission__start_date", "mission_id")
    )

    result: dict[int, list[dict]] = defaultdict(list)
    for assignment in qs:
        result[assignment.user_id].append(
            {
                "mission_id": assignment.mission_id,
                "mission_name": assignment.mission.name,
                "mission_status": assignment.mission.status,
                "assignment_status": assignment.status,
            }
        )
    return dict(result)


def _accepted_assignments_qs(mission: Mission) -> QuerySet[Assignment]:
    """The accepted assignments that actually staff `mission`.

    Deactivated members do not staff anything: `user_update` can flip `is_active` long
    after someone accepted, and a member who can no longer log in cannot serve, so they
    stop filling seats and stop counting toward `min_crew`/`max_crew`. Filtering here —
    the one place both `mission_coverage` and `staffing_validation_errors` read accepted
    assignments from — keeps the two from disagreeing.

    Role is deliberately NOT filtered. Spec §9's "only crew members (role = CREW_MEMBER,
    active) are assignable" is a guard on *creating* an assignment; promoting a serving
    member to mission lead should not silently un-staff an approved mission, whereas
    deactivating their account genuinely removes them.
    """
    return Assignment.objects.filter(
        mission=mission, status=AssignmentStatus.ACCEPTED, user__is_active=True
    )


@dataclass
class RequirementCoverage:
    requirement_id: int
    skill_id: int
    skill_name: str
    min_proficiency: int
    required_count: int
    filled_count: int = 0
    filled_by: list[dict] = field(default_factory=list)


@dataclass
class CoverageReport:
    requirements: list[RequirementCoverage]
    accepted_count: int
    fully_covered: bool


def mission_coverage(mission: Mission) -> CoverageReport:
    """Which requirement seats the mission's *accepted, active* crew fill.

    Per spec §9: a member may count toward requirements of different skills at once,
    but fills at most one requirement row per skill. Within a skill, rows are served
    most-demanding-first from the qualified crew sorted by proficiency descending —
    exact for this nested structure (anyone qualified for a row also qualifies for
    every less demanding row), so no search is needed.

    At most three queries regardless of crew or requirement count.
    """
    requirements = list(
        mission.requirements.select_related("skill").order_by(
            "skill__name", "-min_proficiency", "id"
        )
    )
    accepted = list(_accepted_assignments_qs(mission).select_related("user"))
    accepted_users = {a.user_id: a.user for a in accepted}

    # One pass over the accepted crew's proficiencies in the required skills, grouped
    # into a per-skill pool: highest proficiency first, user id breaking ties so the
    # report is deterministic. No query runs inside the seat-filling loops below.
    pool_by_skill: dict[int, list[tuple[int, int]]] = defaultdict(list)
    if requirements and accepted_users:
        crew_skills = CrewSkill.objects.filter(
            user_id__in=list(accepted_users),
            skill_id__in={r.skill_id for r in requirements},
        ).values_list("user_id", "skill_id", "proficiency")
        for user_id, skill_id, proficiency in crew_skills:
            pool_by_skill[skill_id].append((proficiency, user_id))
        for pool in pool_by_skill.values():
            pool.sort(key=lambda t: (-t[0], t[1]))

    coverages = [
        RequirementCoverage(
            requirement_id=r.id,
            skill_id=r.skill_id,
            skill_name=r.skill.name,
            min_proficiency=r.min_proficiency,
            required_count=r.required_count,
        )
        for r in requirements
    ]
    by_skill: dict[int, list[RequirementCoverage]] = defaultdict(list)
    for coverage in coverages:
        by_skill[coverage.skill_id].append(coverage)

    for skill_id, rows in by_skill.items():
        rows.sort(key=lambda c: (-c.min_proficiency, c.requirement_id))
        pool = pool_by_skill.get(skill_id, [])
        next_free = 0  # each member fills at most one row of this skill
        for coverage in rows:
            while coverage.filled_count < coverage.required_count and next_free < len(pool):
                proficiency, user_id = pool[next_free]
                if proficiency < coverage.min_proficiency:
                    break  # pool is sorted desc, so nobody left qualifies for this row
                next_free += 1
                coverage.filled_count += 1
                coverage.filled_by.append(
                    {
                        "user_id": user_id,
                        "name": accepted_users[user_id].name,
                        "proficiency": proficiency,
                    }
                )

    return CoverageReport(
        requirements=coverages,
        accepted_count=len(accepted),
        fully_covered=all(c.filled_count >= c.required_count for c in coverages),
    )


def mission_conflict_errors(mission: Mission) -> list[str]:
    """Hard-block conflicts held by this mission's own accepted crew, human-readable.

    This is the "conflicts" slice of `staffing_validation_errors` on its own, factored
    out so the activate guard can re-run *only* this check (spec §8's "re-runs conflict
    check (belt and braces)") without restating the hard-block predicate or re-deriving
    the query -- it calls the same one query `staffing_validation_errors` uses.
    """
    # One query: the hard blocks (elsewhere) held by this mission's own accepted crew.
    # Ordered so each member's earliest competing commitment is the one reported.
    blocking = (
        _hard_block_qs(
            start_date=mission.start_date,
            end_date=mission.end_date,
            exclude_mission_id=mission.id,
        )
        .filter(user_id__in=_accepted_assignments_qs(mission).values("user_id"))
        .select_related("mission", "user")
        .order_by("user__name", "user_id", "mission__start_date", "mission_id")
    )
    errors: list[str] = []
    seen: set[int] = set()
    for assignment in blocking:
        if assignment.user_id in seen:
            continue
        seen.add(assignment.user_id)
        errors.append(f"{assignment.user.name} is committed to '{assignment.mission.name}'.")
    return errors


def staffing_validation_errors(mission: Mission) -> list[str]:
    """Human-readable reasons the mission is not ready to be approved (empty = ready).

    Full validation: coverage, crew bounds, and conflicts. Used by the approve guard.
    The activate guard's belt-and-braces re-check calls `mission_conflict_errors`
    directly instead, since coverage/crew-bounds cannot regress between approval and
    activation without going through `assignment_remove`, which is a lead/director
    action independent of the FSM -- re-proving it at activate would wrongly block an
    already-approved mission over crew changes the activate guard was never meant to
    police (only fresh conflicts from other missions being approved in the interim).
    """
    report = mission_coverage(mission)
    errors = [
        f"Requirement {c.skill_name} ≥{c.min_proficiency} needs "
        f"{c.required_count}, has {c.filled_count}."
        for c in report.requirements
        if c.filled_count < c.required_count
    ]

    if report.accepted_count < mission.min_crew:
        errors.append(
            f"Mission needs at least {mission.min_crew} accepted crew (min_crew); "
            f"has {report.accepted_count}."
        )
    if report.accepted_count > mission.max_crew:
        errors.append(
            f"Mission has {report.accepted_count} accepted crew, "
            f"exceeding max_crew ({mission.max_crew})."
        )

    errors.extend(mission_conflict_errors(mission))
    return errors
