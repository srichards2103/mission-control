"""Auto-matching: propose a crew for a mission's still-open requirement seats.

Greedy set-cover. Each round every candidate is asked how many open seats they could
take (at most one per skill, the most demanding row they qualify for); the candidate
covering the most seats wins, ties going to the higher score and then to the lower user
id. That preference order is the whole point of the feature: a generalist who covers two
requirements is worth more to a mission than a specialist who overshoots one.

Three properties this module is built to keep, in priority order:

* **It never restates the availability rule.** `missions.selectors.staffing` owns
  hard blocks, soft conflicts and coverage; every date/status predicate here is a call
  into it. There is deliberately no date lookup and no mission-status set in this file.
* **It is deterministic.** Every ordering is total — score comparisons always terminate
  in an ascending-`user_id` tie-break — so identical data always yields byte-identical
  output. A matcher that shuffles on refresh reads as broken.
* **It is constant-query.** Nine queries whatever the roster size: coverage (3), this
  mission's live assignments, the hard blocks, the crew roster, their proficiencies,
  their committed days, their soft conflicts. Nothing runs inside a loop. (Fewer when a
  set is empty and Django short-circuits an `__in=[]` lookup without hitting the DB.)

Everything returned is plain data — `dataclasses.asdict` produces a JSON-serialisable
tree, which is what Task 5.2's endpoint serialises.
"""

import datetime as dt
from dataclasses import dataclass, field

from mission_control.missions.models import LIVE_ASSIGNMENT_STATUSES, Assignment, Mission
from mission_control.missions.selectors.staffing import (
    committed_assignments,
    hard_blocked_user_ids,
    mission_coverage,
    soft_conflicts_for_users,
)
from mission_control.tenants.context import require_current_tenant_id
from mission_control.users.models import CrewSkill, User
from mission_control.users.roles import Role

W_PROFICIENCY = 1.0
W_WORKLOAD = 0.5
W_SOFT_CONFLICT = 0.75
WORKLOAD_WINDOW_DAYS = 90

#: Proficiency runs 1..10, so the widest possible overshoot of a requirement is 9.
#: Dividing by it normalises `proficiency_fit` onto 0..1.
PROFICIENCY_SPAN = 9

#: How many bench candidates to offer per requirement.
MAX_ALTERNATIVES = 3

#: The closed set of diagnoses for a seat the matcher could not fill. Task 5.3 branches
#: on these strings, so they are constants rather than literals at the point of use.
#: They are mutually exclusive and tested in this order:
#:   1. nobody on the roster qualifies at all;
#:   2. qualified crew exist but every one of them is hard-blocked elsewhere;
#:   3. crew are available but the mission is already at `max_crew` (`open_capacity == 0`);
#:   4. otherwise — there is room and nobody is blocked, the roster is simply too thin.
#: Reasons 3 and 4 are deliberately split: reporting "max_crew too small" alongside an
#: `open_capacity` of 3 is a self-contradictory payload, and 5.3 renders both on one panel.
NO_QUALIFIED_CREW = "no qualified crew"
ALL_QUALIFIED_UNAVAILABLE = "all qualified crew unavailable"
MAX_CREW_TOO_SMALL = "max_crew too small"
NOT_ENOUGH_QUALIFIED_CREW = "not enough qualified crew"


@dataclass
class ProposedMember:
    user_id: int
    name: str
    seats: list[dict] = field(default_factory=list)
    score: float = 0.0
    breakdown: dict = field(default_factory=dict)
    workload_days: int = 0
    soft_conflicts: list[dict] = field(default_factory=list)


@dataclass
class UnfilledSeat:
    requirement_id: int
    skill_name: str
    min_proficiency: int
    reason: str


@dataclass
class RequirementAlternatives:
    requirement_id: int
    skill_name: str
    min_proficiency: int
    candidates: list[dict]


@dataclass
class MatchResult:
    team: list[ProposedMember]
    unfilled_seats: list[UnfilledSeat]
    alternatives: list[RequirementAlternatives]
    open_capacity: int


@dataclass
class _OpenSeat:
    """A requirement row with seats still to fill. Internal to the greedy loop."""

    requirement_id: int
    skill_id: int
    skill_name: str
    min_proficiency: int
    open_count: int


def _proficiency_fit(proficiency: int, min_proficiency: int) -> float:
    """How far a candidate overshoots a requirement, normalised onto 0..1."""
    return (proficiency - min_proficiency) / PROFICIENCY_SPAN


def _committed_days(
    *, user_ids: list[int], window_start: dt.date, window_end: dt.date
) -> dict[int, int]:
    """Days each user is already committed inside the window, keyed by user id.

    Each commitment is clipped to the window before counting, so a year-long mission
    that only clips the edge of the window contributes only the overlapping days.
    Overlapping commitments would double-count, but they cannot exist: two accepted
    assignments on overlapping approved/active missions is precisely what the hard-block
    rule (and the approve guard that enforces it) prevents.

    The mission being staffed is deliberately not excluded, and cannot contribute
    anyway: only pool members are measured, and anyone already live on this mission was
    dropped from the pool before we get here.
    """
    days: dict[int, int] = {}
    for assignment in committed_assignments(
        user_ids=user_ids, start_date=window_start, end_date=window_end
    ):
        start = max(assignment.mission.start_date, window_start)
        end = min(assignment.mission.end_date, window_end)
        days[assignment.user_id] = days.get(assignment.user_id, 0) + (end - start).days + 1
    return days


def match_mission(mission: Mission) -> MatchResult:
    """Propose crew for `mission`'s open seats, with the reasoning behind each pick."""
    coverage = mission_coverage(mission)

    # 1. Open seats. Accepted crew already hold their seats: coverage subtracts them, so
    #    the matcher plans around the existing team rather than re-planning it.
    #    Coverage order (skill name, then most demanding first) carries through to the
    #    unfilled-seat list, so the output is stable and reads in a sensible order.
    open_seats = [
        _OpenSeat(
            requirement_id=c.requirement_id,
            skill_id=c.skill_id,
            skill_name=c.skill_name,
            min_proficiency=c.min_proficiency,
            open_count=c.required_count - c.filled_count,
        )
        for c in coverage.requirements
        if c.filled_count < c.required_count
    ]

    # 2. The pool: active crew of this tenant, minus anyone hard-blocked elsewhere,
    #    minus anyone already proposed or accepted here (they are not a new proposal).
    #
    #    `user__is_active=True` mirrors `staffing._accepted_assignments_qs`, per the
    #    human ruling that deactivated crew do not fill staffing seats. Without it a
    #    member deactivated after being proposed would still consume a `max_crew` seat
    #    and count toward `min_crew`, so the matcher would under-propose and hand back a
    #    team the approve guard then rejects as short — with nothing explaining why.
    #    Such a member is already absent from `roster` below, so freeing their seat here
    #    cannot re-propose them; it only stops them holding a seat nobody can use.
    live_user_ids = set(
        Assignment.objects.filter(
            mission=mission, status__in=LIVE_ASSIGNMENT_STATUSES, user__is_active=True
        ).values_list("user_id", flat=True)
    )
    capacity = max(mission.max_crew - len(live_user_ids), 0)

    blocked_ids = hard_blocked_user_ids(
        start_date=mission.start_date,
        end_date=mission.end_date,
        exclude_mission_id=mission.id,
    )
    # `User.objects` is not tenant-scoped (auth resolves users before any tenant
    # context exists), so the tenant filter here is mandatory, not belt and braces.
    roster = list(
        User.objects.filter(
            tenant_id=require_current_tenant_id(), role=Role.CREW_MEMBER, is_active=True
        ).order_by("id")
    )
    pool: dict[int, User] = {
        u.id: u for u in roster if u.id not in blocked_ids and u.id not in live_user_ids
    }

    # 3. Candidate metrics, all fetched in bulk up front — nothing below queries.
    required_skill_ids = {c.skill_id for c in coverage.requirements}
    proficiencies: dict[int, dict[int, int]] = {}
    if roster and required_skill_ids:
        rows = CrewSkill.objects.filter(
            user_id__in=[u.id for u in roster], skill_id__in=required_skill_ids
        ).values_list("user_id", "skill_id", "proficiency")
        for user_id, skill_id, proficiency in rows:
            proficiencies.setdefault(user_id, {})[skill_id] = proficiency

    workload = _committed_days(
        user_ids=list(pool),
        window_start=mission.start_date - dt.timedelta(days=WORKLOAD_WINDOW_DAYS),
        window_end=mission.end_date + dt.timedelta(days=WORKLOAD_WINDOW_DAYS),
    )
    conflicts = soft_conflicts_for_users(
        user_ids=list(pool),
        start_date=mission.start_date,
        end_date=mission.end_date,
        exclude_mission_id=mission.id,
    )

    def proficiency_in(user_id: int, skill_id: int) -> int:
        return proficiencies.get(user_id, {}).get(skill_id, 0)

    def coverable_seats(user_id: int) -> list[tuple[_OpenSeat, int]]:
        """The open seats this candidate could take: at most one per skill.

        Spec §9's rule for coverage applies to proposals too — one person cannot fill
        two seats of the same skill — so within a skill they take the most demanding
        row they qualify for, leaving the easier rows to less experienced crew.
        """
        best_per_skill: dict[int, tuple[_OpenSeat, int]] = {}
        for seat in open_seats:
            if seat.open_count <= 0:
                continue
            proficiency = proficiency_in(user_id, seat.skill_id)
            if proficiency < seat.min_proficiency:
                continue
            current = best_per_skill.get(seat.skill_id)
            if current is None or (seat.min_proficiency, -seat.requirement_id) > (
                current[0].min_proficiency,
                -current[0].requirement_id,
            ):
                best_per_skill[seat.skill_id] = (seat, proficiency)
        return [best_per_skill[skill_id] for skill_id in sorted(best_per_skill)]

    def score_for(user_id: int, fits: list[float]) -> tuple[float, dict]:
        """`W_PROFICIENCY·mean_fit + W_WORKLOAD·balance − W_SOFT_CONFLICT·penalty`."""
        mean_fit = sum(fits) / len(fits) if fits else 0.0
        balance = 1 - min(workload.get(user_id, 0) / WORKLOAD_WINDOW_DAYS, 1)
        penalty = 1.0 if conflicts.get(user_id) else 0.0
        score = W_PROFICIENCY * mean_fit + W_WORKLOAD * balance - W_SOFT_CONFLICT * penalty
        breakdown = {
            "proficiency_fit": round(mean_fit, 3),
            "workload_balance": round(balance, 3),
            "soft_conflict_penalty": penalty,
        }
        return score, breakdown

    def take(
        user_id: int, seats: list[tuple[_OpenSeat, int]], score: float, breakdown: dict
    ) -> ProposedMember:
        """Move a candidate from the pool onto the team, claiming their seats."""
        user = pool.pop(user_id)
        for seat, _proficiency in seats:
            seat.open_count -= 1
        return ProposedMember(
            user_id=user_id,
            name=user.name,
            seats=[
                {
                    "requirement_id": seat.requirement_id,
                    "skill_name": seat.skill_name,
                    "min_proficiency": seat.min_proficiency,
                    "proficiency": proficiency,
                }
                for seat, proficiency in seats
            ],
            score=round(score, 3),
            breakdown=breakdown,
            workload_days=workload.get(user_id, 0),
            soft_conflicts=conflicts.get(user_id, []),
        )

    # 4. Greedy cover: most seats, then best score, then lowest user id.
    team: list[ProposedMember] = []
    while capacity > 0 and pool and any(seat.open_count > 0 for seat in open_seats):
        best: tuple[tuple, int, list, float, dict] | None = None
        for user_id in pool:
            seats = coverable_seats(user_id)
            if not seats:
                continue
            score, breakdown = score_for(
                user_id, [_proficiency_fit(p, seat.min_proficiency) for seat, p in seats]
            )
            key = (-len(seats), -score, user_id)
            if best is None or key < best[0]:
                best = (key, user_id, seats, score, breakdown)
        if best is None:
            break  # nobody left can cover anything, though seats remain
        _key, user_id, seats, score, breakdown = best
        team.append(take(user_id, seats, score, breakdown))
        capacity -= 1

    # 5. Top up to min_crew with the best-scoring crew left, seats or no seats: the
    #    mission cannot be approved short of min_crew even when every seat is covered.
    if capacity > 0 and len(live_user_ids) + len(team) < mission.min_crew:
        # Scores do not change as members leave the pool, so one sort is enough.
        ranked = sorted(pool, key=lambda uid: (-score_for(uid, [])[0], uid))
        for user_id in ranked:
            if capacity <= 0 or len(live_user_ids) + len(team) >= mission.min_crew:
                break
            score, breakdown = score_for(user_id, [])
            team.append(take(user_id, [], score, breakdown))
            capacity -= 1

    # 6. Diagnose what is still open, so the UI can say *why* rather than just "short".
    #    Availability is judged against the hard blocks, not against who is left in the
    #    pool: a candidate the matcher already seated elsewhere was available. `capacity`
    #    here is the final `open_capacity`, so "max_crew too small" is only ever reported
    #    when the mission genuinely has no room left.
    unfilled: list[UnfilledSeat] = []
    for seat in open_seats:
        if seat.open_count <= 0:
            continue
        qualified = {
            u.id for u in roster if proficiency_in(u.id, seat.skill_id) >= seat.min_proficiency
        }
        if not qualified:
            reason = NO_QUALIFIED_CREW
        elif qualified <= blocked_ids:
            reason = ALL_QUALIFIED_UNAVAILABLE
        elif capacity == 0:
            reason = MAX_CREW_TOO_SMALL
        else:
            reason = NOT_ENOUGH_QUALIFIED_CREW
        unfilled.extend(
            UnfilledSeat(seat.requirement_id, seat.skill_name, seat.min_proficiency, reason)
            for _ in range(seat.open_count)
        )

    # 7. Alternatives: the bench for each requirement — qualified, available, and not
    #    already proposed (the team members were popped from the pool as they were
    #    taken). Scored as if they took this one seat, so the number shown explains the
    #    order; ties break on ascending user id like everywhere else.
    alternatives: list[RequirementAlternatives] = []
    for cov in coverage.requirements:
        ranked_bench = []
        for user_id, user in pool.items():
            proficiency = proficiency_in(user_id, cov.skill_id)
            if proficiency < cov.min_proficiency:
                continue
            score, _breakdown = score_for(
                user_id, [_proficiency_fit(proficiency, cov.min_proficiency)]
            )
            ranked_bench.append((-score, user_id, proficiency, user.name, score))
        ranked_bench.sort()
        alternatives.append(
            RequirementAlternatives(
                requirement_id=cov.requirement_id,
                skill_name=cov.skill_name,
                min_proficiency=cov.min_proficiency,
                candidates=[
                    {
                        "user_id": user_id,
                        "name": name,
                        "proficiency": proficiency,
                        "score": round(score, 3),
                    }
                    for _neg, user_id, proficiency, name, score in ranked_bench[:MAX_ALTERNATIVES]
                ],
            )
        )

    return MatchResult(
        team=team,
        unfilled_seats=unfilled,
        alternatives=alternatives,
        open_capacity=capacity,
    )
