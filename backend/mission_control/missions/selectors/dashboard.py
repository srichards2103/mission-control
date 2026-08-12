"""Organisation dashboard — read-only aggregates over missions and crew.

Every consumer of the availability/coverage rule goes through
`mission_control.missions.selectors.staffing`; nothing here re-derives the hard-block
predicate, the overlap test, or the `{approved, active}` status set. Where this module
needs "still relevant" (not yet ended) or "starts soon" date filters, those are
deliberately single-sided lookups (`end_date__lt` / `start_date__gt`, both negated via
`.exclude()`) rather than the `start_date__lte` / `end_date__gte` pair that make up the
two-range overlap test owned by `staffing.py` — a dashboard "is this still open"
filter is a different question from "do these two ranges overlap".

Query-count discipline:
  * `pipeline_summary`, `crew_utilization`, `skill_gaps` are all O(1) queries,
    regardless of how many missions/crew/skills exist — verified in
    `tests/missions/test_dashboard.py` at two data sizes each.
  * `staffing_readiness` calls `mission_coverage` once per *currently live* mission
    (pending_approval/approved/active, not yet ended) — the bounded, on-screen working
    set, not the organisation's full mission history. Its query count is linear in
    that count (1 + 3*N); the test asserts the formula holds and that irrelevant
    (draft/completed/cancelled/rejected) history does not add queries.
"""

import datetime as dt
from collections import defaultdict

from django.db.models import Count, F, Min, OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce

from mission_control.missions.models import (
    Mission,
    MissionRequirement,
    MissionStatus,
    MissionTransition,
)
from mission_control.missions.selectors.staffing import committed_assignments, mission_coverage
from mission_control.tenants.context import require_current_tenant_id
from mission_control.users.models import CrewSkill, User
from mission_control.users.roles import Role

OPEN_STATUSES = frozenset(
    {
        MissionStatus.DRAFT,
        MissionStatus.PENDING_APPROVAL,
        MissionStatus.APPROVED,
        MissionStatus.ACTIVE,
    }
)

_READINESS_STATUSES = (
    MissionStatus.PENDING_APPROVAL,
    MissionStatus.APPROVED,
    MissionStatus.ACTIVE,
)

_UPCOMING_STATUSES = (MissionStatus.DRAFT, MissionStatus.PENDING_APPROVAL, MissionStatus.APPROVED)

_UPCOMING_WINDOW_DAYS = 30


def pipeline_summary() -> dict:
    """Status counts, the pending-approval queue, and missions starting soon.

    Three queries total, regardless of how many missions exist:
      1. one grouped count for `status_counts`,
      2. one query for the pending-approval queue, with `submitted_at` computed by a
         correlated subquery (latest transition into pending_approval) rather than a
         per-mission lookup,
      3. one query for `upcoming`.
    """
    today = dt.date.today()

    counts = dict.fromkeys(MissionStatus.values, 0)
    for row in Mission.objects.values("status").annotate(n=Count("id")):
        counts[row["status"]] = row["n"]

    latest_submission = (
        MissionTransition.objects.filter(
            mission=OuterRef("pk"), to_status=MissionStatus.PENDING_APPROVAL
        )
        .order_by("-created_at")
        .values("created_at")[:1]
    )
    pending_qs = (
        Mission.objects.filter(status=MissionStatus.PENDING_APPROVAL)
        .annotate(submitted_at=Coalesce(Subquery(latest_submission), F("created_at")))
        .order_by("submitted_at")
    )
    pending_approvals = [
        {
            "mission_id": m.id,
            "name": m.name,
            "submitted_at": m.submitted_at,
            "age_days": (today - m.submitted_at.date()).days,
        }
        for m in pending_qs
    ]

    upcoming_qs = (
        Mission.objects.filter(status__in=_UPCOMING_STATUSES, start_date__gte=today)
        # NOT start_date__lte(today + 30): avoids restating the overlap-test lookup
        # pair owned by staffing.py, even though this is a single-sided filter.
        .exclude(start_date__gt=today + dt.timedelta(days=_UPCOMING_WINDOW_DAYS))
        .order_by("start_date")
    )
    upcoming = [
        {
            "mission_id": m.id,
            "name": m.name,
            "start_date": m.start_date,
            "days_until": (m.start_date - today).days,
        }
        for m in upcoming_qs
    ]

    return {"status_counts": counts, "pending_approvals": pending_approvals, "upcoming": upcoming}


def staffing_readiness() -> list[dict]:
    """Coverage snapshot for every currently live mission, at-risk ones first.

    "Live" = pending_approval/approved/active and not yet ended. Delegates every seat
    computation to `mission_coverage` — coverage/fully-covered/accepted-count are never
    recomputed here. See module docstring for the query-count characteristics.
    """
    today = dt.date.today()
    missions = (
        Mission.objects.filter(status__in=_READINESS_STATUSES)
        # NOT end_date__gte(today): see module docstring.
        .exclude(end_date__lt=today)
        .order_by("start_date")
    )

    rows = []
    for mission in missions:
        report = mission_coverage(mission)
        total_seats = sum(c.required_count for c in report.requirements)
        filled_seats = sum(c.filled_count for c in report.requirements)
        coverage_pct = round(100 * filled_seats / total_seats) if total_seats else 100
        at_risk = not report.fully_covered or report.accepted_count < mission.min_crew
        rows.append(
            {
                "mission_id": mission.id,
                "name": mission.name,
                "status": mission.status,
                "start_date": mission.start_date,
                "coverage_pct": coverage_pct,
                "accepted_count": report.accepted_count,
                "min_crew": mission.min_crew,
                "fully_covered": report.fully_covered,
                "at_risk": at_risk,
            }
        )

    rows.sort(key=lambda r: (not r["at_risk"], r["start_date"]))
    return rows


def crew_utilization(window_days: int = 90) -> dict:
    """Accepted-assignment load per active crew member over `[today, today+window_days)`.

    "Committed" here is exactly the hard-block predicate (accepted assignment on an
    approved/active mission) — so this calls `committed_assignments` rather than
    restating "approved/active" or the overlap test. Two queries total: the crew list
    and the committed assignments, both independent of how many missions or crew exist.
    """
    today = dt.date.today()
    window_end = today + dt.timedelta(days=window_days - 1)

    crew = list(
        User.objects.filter(
            tenant_id=require_current_tenant_id(), role=Role.CREW_MEMBER, is_active=True
        ).order_by("name")
    )
    crew_ids = [u.id for u in crew]

    assigned_days: dict[int, int] = defaultdict(int)
    assignments = committed_assignments(user_ids=crew_ids, start_date=today, end_date=window_end)
    for assignment in assignments:
        clipped_start = max(assignment.mission.start_date, today)
        clipped_end = min(assignment.mission.end_date, window_end)
        assigned_days[assignment.user_id] += (clipped_end - clipped_start).days + 1

    rows = [
        {
            "user_id": u.id,
            "name": u.name,
            "assigned_days": assigned_days.get(u.id, 0),
            "utilization_pct": round(100 * assigned_days.get(u.id, 0) / window_days),
        }
        for u in crew
    ]
    rows.sort(key=lambda r: (-r["assigned_days"], r["name"]))

    org_utilization_pct = (
        round(sum(r["utilization_pct"] for r in rows) / len(rows)) if rows else 0
    )
    return {"window_days": window_days, "org_utilization_pct": org_utilization_pct, "crew": rows}


def skill_gaps() -> list[dict]:
    """Per-skill open-seat demand vs. qualified active crew, for open missions.

    "Open" = draft/pending_approval/approved/active and not yet ended. Two queries
    total, independent of how many skills/missions/crew exist: one grouped aggregate
    for seat totals and per-skill proficiency thresholds, one for the crew who qualify
    against every threshold at once (grouped in Python, not one query per skill).
    """
    today = dt.date.today()
    requirement_rows = list(
        MissionRequirement.objects.filter(mission__status__in=OPEN_STATUSES)
        # NOT mission__end_date__gte(today): see module docstring.
        .exclude(mission__end_date__lt=today)
        .values("skill_id", "skill__name")
        .annotate(open_seats=Sum("required_count"), threshold=Min("min_proficiency"))
        .order_by()
    )
    if not requirement_rows:
        return []

    skill_ids = [row["skill_id"] for row in requirement_rows]
    thresholds = {row["skill_id"]: row["threshold"] for row in requirement_rows}

    qualified_users: dict[int, set[int]] = defaultdict(set)
    crew_skill_rows = CrewSkill.objects.filter(
        skill_id__in=skill_ids, user__role=Role.CREW_MEMBER, user__is_active=True
    ).values_list("skill_id", "user_id", "proficiency")
    for skill_id, user_id, proficiency in crew_skill_rows:
        if proficiency >= thresholds[skill_id]:
            qualified_users[skill_id].add(user_id)

    gaps = []
    for row in requirement_rows:
        skill_id = row["skill_id"]
        open_seats = row["open_seats"]
        qualified_crew = len(qualified_users.get(skill_id, ()))
        gaps.append(
            {
                "skill_id": skill_id,
                "skill_name": row["skill__name"],
                "open_seats": open_seats,
                "qualified_crew": qualified_crew,
                "gap": open_seats > qualified_crew,
            }
        )

    gaps.sort(key=lambda g: (not g["gap"], g["skill_name"]))
    return gaps
