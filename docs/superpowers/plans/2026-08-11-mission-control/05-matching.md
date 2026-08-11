# Stage 5: Matching Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Global constraints in `00-overview.md` apply to every task.

**Goal:** The greedy weighted set-cover matcher (pure function, explanations, alternatives, infeasibility diagnoses), its API, and the matcher dialog with swap + bulk propose.

**Architecture:** `match_mission` reuses the Stage 4 staffing selectors (one availability implementation) and returns dataclasses; the API is a thin serialization. Weights are module constants — spec §10 marks them tunable at implementation, so calibrating them later only touches one place.

**Tech Stack:** See `00-overview.md`.

---

### Task 5.1: Matching engine

**Files:**
- Create: `backend/mission_control/missions/services/matching.py`, `backend/tests/missions/test_matching.py`

**Interfaces:**
- Produces (`missions.services.matching`):
  - Constants: `W_PROFICIENCY = 1.0`, `W_WORKLOAD = 0.5`, `W_SOFT_CONFLICT = 0.75`, `WORKLOAD_WINDOW_DAYS = 90`
  - `match_mission(mission) -> MatchResult` — dataclasses (all JSON-serializable via `dataclasses.asdict`):
    - `ProposedMember(user_id, name, seats: list[dict], score: float, breakdown: dict, workload_days: int, soft_conflicts: list[dict])` — `seats` entries `{"requirement_id", "skill_name", "min_proficiency", "proficiency"}`; `breakdown` = `{"proficiency_fit", "workload_balance", "soft_conflict_penalty"}`
    - `UnfilledSeat(requirement_id, skill_name, min_proficiency, reason)` — reason ∈ `"no qualified crew"` / `"all qualified crew unavailable"` / `"max_crew too small"`
    - `RequirementAlternatives(requirement_id, skill_name, min_proficiency, candidates: list[dict])` — up to 3 `{"user_id", "name", "proficiency", "score"}` ranked by score, pool members not in the proposed team
    - `MatchResult(team, unfilled_seats, alternatives, open_capacity: int)`
  - Algorithm (spec §10, deterministic — every sort tie-breaks on ascending `user_id`):
    1. Open seats = per requirement row, `required_count − filled_count` from `mission_coverage(mission)` (existing accepted crew are respected, not re-planned).
    2. Pool = active CREW_MEMBERs of the tenant − `hard_blocked_user_ids(mission range, exclude this mission)` − users already live-assigned to this mission.
    3. Candidate metrics: `proficiency_fit(seat) = (prof − min_proficiency) / 9`; `workload_days` = accepted assignment-days on approved/active missions overlapping `[start−90d, end+90d]`; `workload_balance = 1 − min(workload_days / 90, 1)`; `soft_conflict_penalty = 1` if any soft conflict for the mission range else `0`; `score = W_PROFICIENCY·mean_fit_over_coverable_seats + W_WORKLOAD·balance − W_SOFT_CONFLICT·penalty`.
    4. Greedy: capacity = `max_crew −` live assignment count. Repeat: each pool candidate may take **at most one open seat per skill** (the most demanding they qualify for); pick the candidate with (most seats covered, highest score, lowest id); assign, shrink seats, drop from pool. Stop at capacity / no seats / no coverage.
    5. Top-up: while live + team < `min_crew` and capacity remains, add best-scoring remaining pool members (zero seats).
    6. Diagnose each still-open seat: nobody in the tenant qualifies → `no qualified crew`; qualified people exist but all were hard-blocked → `all qualified crew unavailable`; otherwise → `max_crew too small`.
- Consumes: `mission_coverage`, `hard_blocked_user_ids`, `soft_conflicts_for_users`, `CrewSkill`, `Assignment`

- [ ] **Step 1: Write the failing tests**

`backend/tests/missions/test_matching.py`:

```python
import dataclasses
import datetime as dt

import pytest

from mission_control.missions.factories import (
    AssignmentFactory, MissionFactory, MissionRequirementFactory,
)
from mission_control.missions.models import AssignmentStatus, MissionStatus
from mission_control.missions.services.matching import match_mission
from mission_control.tenants.context import set_current_tenant_id
from mission_control.users.factories import CrewSkillFactory, SkillFactory, UserFactory
from mission_control.users.roles import Role

pytestmark = pytest.mark.django_db
D = dt.date


@pytest.fixture
def mission():
    m = MissionFactory(start_date=D(2026, 9, 1), end_date=D(2026, 9, 10), min_crew=1, max_crew=4)
    set_current_tenant_id(m.tenant_id)
    return m


def crew_with(mission, skills: dict, name="Crew"):
    user = UserFactory(role=Role.CREW_MEMBER, tenant=mission.tenant, name=name)
    for skill, prof in skills.items():
        CrewSkillFactory(user=user, skill=skill, proficiency=prof)
    return user


def test_assembles_covering_team_with_explanations(mission):
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    nav = SkillFactory(tenant=mission.tenant, name="Navigation")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=6)
    MissionRequirementFactory(mission=mission, skill=nav, min_proficiency=5)
    pilot = crew_with(mission, {piloting: 8}, "Pilot Pat")
    navigator = crew_with(mission, {nav: 7}, "Nav Nia")
    result = match_mission(mission)
    assert {m.user_id for m in result.team} == {pilot.id, navigator.id}
    assert result.unfilled_seats == []
    pat = next(m for m in result.team if m.user_id == pilot.id)
    assert pat.seats[0]["skill_name"] == "Piloting"
    assert set(pat.breakdown) == {"proficiency_fit", "workload_balance", "soft_conflict_penalty"}


def test_generalist_preferred_over_specialists(mission):
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    nav = SkillFactory(tenant=mission.tenant, name="Navigation")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5)
    MissionRequirementFactory(mission=mission, skill=nav, min_proficiency=5)
    crew_with(mission, {piloting: 9}, "Specialist P")
    crew_with(mission, {nav: 9}, "Specialist N")
    generalist = crew_with(mission, {piloting: 6, nav: 6}, "Generalist G")
    result = match_mission(mission)
    assert result.team[0].user_id == generalist.id
    assert len(result.team[0].seats) == 2


def test_workload_balance_breaks_tie(mission):
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5)
    busy = crew_with(mission, {piloting: 7}, "Busy")
    fresh = crew_with(mission, {piloting: 7}, "Fresh")
    other = MissionFactory(tenant=mission.tenant, status=MissionStatus.ACTIVE,
                           start_date=D(2026, 8, 1), end_date=D(2026, 8, 30))
    AssignmentFactory(mission=other, user=busy, status=AssignmentStatus.ACCEPTED)
    result = match_mission(mission)
    assert result.team[0].user_id == fresh.id


def test_existing_accepted_crew_reduce_open_seats(mission):
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5, required_count=2)
    covered = crew_with(mission, {piloting: 8}, "Already In")
    AssignmentFactory(mission=mission, user=covered, status=AssignmentStatus.ACCEPTED)
    crew_with(mission, {piloting: 7}, "Candidate")
    result = match_mission(mission)
    assert len(result.team) == 1  # only one open seat left
    assert result.team[0].name == "Candidate"


def test_infeasible_diagnoses(mission):
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    welding = SkillFactory(tenant=mission.tenant, name="Welding")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=9)
    MissionRequirementFactory(mission=mission, skill=welding, min_proficiency=5)
    crew_with(mission, {piloting: 6}, "Underqualified")
    blocked = crew_with(mission, {welding: 8}, "Blocked")
    blocker = MissionFactory(tenant=mission.tenant, status=MissionStatus.ACTIVE,
                             start_date=D(2026, 9, 5), end_date=D(2026, 9, 15))
    AssignmentFactory(mission=blocker, user=blocked, status=AssignmentStatus.ACCEPTED)
    result = match_mission(mission)
    reasons = {u.skill_name: u.reason for u in result.unfilled_seats}
    assert reasons == {"Piloting": "no qualified crew", "Welding": "all qualified crew unavailable"}


def test_top_up_to_min_crew(mission):
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5)
    mission.min_crew = 2
    mission.save()
    crew_with(mission, {piloting: 8}, "Pilot")
    crew_with(mission, {}, "Extra Hands")
    result = match_mission(mission)
    assert len(result.team) == 2


def test_alternatives_exclude_team(mission):
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5)
    for i, prof in enumerate((9, 8, 7, 6)):
        crew_with(mission, {piloting: prof}, f"P{i}")
    result = match_mission(mission)
    alt = result.alternatives[0]
    team_ids = {m.user_id for m in result.team}
    assert len(alt.candidates) == 3
    assert team_ids.isdisjoint({c["user_id"] for c in alt.candidates})


def test_deterministic(mission):
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5, required_count=2)
    for i in range(5):
        crew_with(mission, {piloting: 7}, f"Twin {i}")
    r1, r2 = match_mission(mission), match_mission(mission)
    assert dataclasses.asdict(r1) == dataclasses.asdict(r2)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/missions/test_matching.py -v` — Expected: FAIL (module missing).

- [ ] **Step 3: Implement `missions/services/matching.py`**

```python
import datetime as dt
from collections import defaultdict
from dataclasses import dataclass, field

from mission_control.missions.models import (
    Assignment, AssignmentStatus, LIVE_ASSIGNMENT_STATUSES, Mission,
)
from mission_control.missions.selectors.staffing import (
    HARD_BLOCK_MISSION_STATUSES, hard_blocked_user_ids, mission_coverage, soft_conflicts_for_users,
)
from mission_control.tenants.context import require_current_tenant_id
from mission_control.users.models import CrewSkill, User
from mission_control.users.roles import Role

W_PROFICIENCY = 1.0
W_WORKLOAD = 0.5
W_SOFT_CONFLICT = 0.75
WORKLOAD_WINDOW_DAYS = 90


@dataclass
class ProposedMember:
    user_id: int
    name: str
    seats: list = field(default_factory=list)
    score: float = 0.0
    breakdown: dict = field(default_factory=dict)
    workload_days: int = 0
    soft_conflicts: list = field(default_factory=list)


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
    candidates: list


@dataclass
class MatchResult:
    team: list
    unfilled_seats: list
    alternatives: list
    open_capacity: int


def _workload_days(user_ids, window_start, window_end) -> dict[int, int]:
    days: dict[int, int] = defaultdict(int)
    rows = (Assignment.objects.filter(
        user_id__in=user_ids, status=AssignmentStatus.ACCEPTED,
        mission__status__in=HARD_BLOCK_MISSION_STATUSES,
        mission__start_date__lte=window_end, mission__end_date__gte=window_start,
    ).select_related("mission"))
    for a in rows:
        start = max(a.mission.start_date, window_start)
        end = min(a.mission.end_date, window_end)
        days[a.user_id] += (end - start).days + 1
    return days


def match_mission(mission: Mission) -> MatchResult:
    coverage = mission_coverage(mission)
    open_seats: dict[int, dict] = {}  # requirement_id -> {skill_id, skill_name, min_proficiency, open}
    for cov in coverage.requirements:
        if cov.filled_count < cov.required_count:
            open_seats[cov.requirement_id] = {
                "skill_id": cov.skill_id, "skill_name": cov.skill_name,
                "min_proficiency": cov.min_proficiency,
                "open": cov.required_count - cov.filled_count,
            }

    live = Assignment.objects.filter(mission=mission, status__in=LIVE_ASSIGNMENT_STATUSES)
    live_user_ids = set(live.values_list("user_id", flat=True))
    capacity = mission.max_crew - len(live_user_ids)

    blocked = hard_blocked_user_ids(
        start_date=mission.start_date, end_date=mission.end_date, exclude_mission_id=mission.id)
    all_crew = list(User.objects.filter(
        tenant_id=require_current_tenant_id(), role=Role.CREW_MEMBER, is_active=True))
    pool = {u.id: u for u in all_crew if u.id not in blocked and u.id not in live_user_ids}

    profs: dict[int, dict[int, int]] = defaultdict(dict)  # user_id -> skill_id -> proficiency
    for cs in CrewSkill.objects.filter(user_id__in=[u.id for u in all_crew]):
        profs[cs.user_id][cs.skill_id] = cs.proficiency

    window_start = mission.start_date - dt.timedelta(days=WORKLOAD_WINDOW_DAYS)
    window_end = mission.end_date + dt.timedelta(days=WORKLOAD_WINDOW_DAYS)
    workload = _workload_days(list(pool), window_start, window_end)
    conflicts = soft_conflicts_for_users(
        user_ids=list(pool), start_date=mission.start_date,
        end_date=mission.end_date, exclude_mission_id=mission.id)

    def coverable(user_id):
        """Most demanding open seat per skill this user qualifies for."""
        best_per_skill: dict[int, tuple] = {}
        for req_id, seat in open_seats.items():
            prof = profs[user_id].get(seat["skill_id"], 0)
            if seat["open"] > 0 and prof >= seat["min_proficiency"]:
                current = best_per_skill.get(seat["skill_id"])
                if current is None or seat["min_proficiency"] > current[1]["min_proficiency"]:
                    best_per_skill[seat["skill_id"]] = (req_id, seat, prof)
        return list(best_per_skill.values())

    def scored(user_id, seats):
        fits = [(prof - seat["min_proficiency"]) / 9 for _, seat, prof in seats]
        mean_fit = sum(fits) / len(fits) if fits else 0.0
        balance = 1 - min(workload.get(user_id, 0) / WORKLOAD_WINDOW_DAYS, 1)
        penalty = 1.0 if conflicts.get(user_id) else 0.0
        score = W_PROFICIENCY * mean_fit + W_WORKLOAD * balance - W_SOFT_CONFLICT * penalty
        breakdown = {"proficiency_fit": round(mean_fit, 3), "workload_balance": round(balance, 3),
                     "soft_conflict_penalty": penalty}
        return score, breakdown

    team: list[ProposedMember] = []
    while capacity > 0 and any(s["open"] > 0 for s in open_seats.values()) and pool:
        candidates = []
        for uid in pool:
            seats = coverable(uid)
            if not seats:
                continue
            score, breakdown = scored(uid, seats)
            candidates.append((len(seats), score, -uid, uid, seats, breakdown))
        if not candidates:
            break
        candidates.sort(reverse=True)
        _, score, _, uid, seats, breakdown = candidates[0]
        user = pool.pop(uid)
        for req_id, seat, _prof in seats:
            open_seats[req_id]["open"] -= 1
        team.append(ProposedMember(
            user_id=uid, name=user.name,
            seats=[{"requirement_id": req_id, "skill_name": seat["skill_name"],
                    "min_proficiency": seat["min_proficiency"], "proficiency": prof}
                   for req_id, seat, prof in seats],
            score=round(score, 3), breakdown=breakdown,
            workload_days=workload.get(uid, 0), soft_conflicts=conflicts.get(uid, []),
        ))
        capacity -= 1

    # Top up to min_crew with best-scoring generalists
    while capacity > 0 and len(live_user_ids) + len(team) < mission.min_crew and pool:
        ranked = sorted(((*scored(uid, []), uid) for uid in pool),
                        key=lambda t: (-t[0], t[2]))
        score, breakdown, uid = ranked[0]
        user = pool.pop(uid)
        team.append(ProposedMember(user_id=uid, name=user.name, score=round(score, 3),
                                   breakdown=breakdown, workload_days=workload.get(uid, 0),
                                   soft_conflicts=conflicts.get(uid, [])))
        capacity -= 1

    # Diagnose unfilled seats
    unfilled = []
    for req_id, seat in sorted(open_seats.items()):
        for _ in range(seat["open"]):
            qualified_anyone = any(
                profs[u.id].get(seat["skill_id"], 0) >= seat["min_proficiency"] for u in all_crew)
            if not qualified_anyone:
                reason = "no qualified crew"
            else:
                qualified_available = any(
                    profs[uid].get(seat["skill_id"], 0) >= seat["min_proficiency"] for uid in pool)
                reason = "max_crew too small" if qualified_available else "all qualified crew unavailable"
            unfilled.append(UnfilledSeat(req_id, seat["skill_name"], seat["min_proficiency"], reason))

    # Alternatives: top 3 qualified pool members per requirement, excluding the team
    team_ids = {m.user_id for m in team}
    alternatives = []
    for cov in coverage.requirements:
        ranked = []
        for uid, user in pool.items():
            if uid in team_ids:
                continue
            prof = profs[uid].get(cov.skill_id, 0)
            if prof >= cov.min_proficiency:
                score, _ = scored(uid, [])
                ranked.append((-score - prof / 100, uid, prof, user.name, score))
        ranked.sort()
        alternatives.append(RequirementAlternatives(
            requirement_id=cov.requirement_id, skill_name=cov.skill_name,
            min_proficiency=cov.min_proficiency,
            candidates=[{"user_id": uid, "name": name, "proficiency": prof, "score": round(s, 3)}
                        for _, uid, prof, name, s in ranked[:3]],
        ))

    return MatchResult(team=team, unfilled_seats=unfilled,
                       alternatives=alternatives, open_capacity=capacity)
```

- [ ] **Step 4: Run tests to verify they pass, commit**

Run: `uv run pytest tests/missions/test_matching.py -v` — Expected: PASS.

```bash
git add -A && git commit -m "feat: greedy set-cover matching engine with explanations and diagnoses"
```

---

### Task 5.2: Match API

**Files:**
- Create: `backend/mission_control/missions/apis/matching.py`, `backend/tests/missions/test_match_api.py`
- Modify: `backend/mission_control/missions/urls.py`

**Interfaces:**
- Produces: `POST /api/v1/missions/<id>/match/` (perm `match.run`) — no side effects; 400 `ApplicationError("Cannot match a completed or cancelled mission.")` on terminal missions; response = `dataclasses.asdict(match_mission(mission))`

- [ ] **Step 1: Write the failing tests**

`backend/tests/missions/test_match_api.py`:

```python
import datetime as dt

import pytest

from mission_control.missions.factories import MissionFactory, MissionRequirementFactory
from mission_control.users.factories import CrewSkillFactory, SkillFactory, UserFactory
from mission_control.users.roles import Role

pytestmark = pytest.mark.django_db


def test_match_returns_team_and_makes_no_assignments(auth_client_for):
    lead = UserFactory(role=Role.MISSION_LEAD)
    mission = MissionFactory(tenant=lead.tenant, created_by=lead,
                             start_date=dt.date(2026, 9, 1), end_date=dt.date(2026, 9, 10))
    skill = SkillFactory(tenant=lead.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=skill, min_proficiency=5)
    crew = UserFactory(role=Role.CREW_MEMBER, tenant=lead.tenant)
    CrewSkillFactory(user=crew, skill=skill, proficiency=8)

    resp = auth_client_for(lead).post(f"/api/v1/missions/{mission.id}/match/")
    assert resp.status_code == 200
    assert resp.data["team"][0]["user_id"] == crew.id
    from mission_control.missions.models import Assignment
    assert Assignment.objects_unscoped.count() == 0  # pure


def test_crew_cannot_run_matcher(auth_client_for):
    crew = UserFactory(role=Role.CREW_MEMBER)
    mission = MissionFactory(tenant=crew.tenant)
    assert auth_client_for(crew).post(f"/api/v1/missions/{mission.id}/match/").status_code == 403


def test_match_terminal_mission_400(auth_client_for):
    lead = UserFactory(role=Role.MISSION_LEAD)
    mission = MissionFactory(tenant=lead.tenant, created_by=lead, status="completed")
    assert auth_client_for(lead).post(f"/api/v1/missions/{mission.id}/match/").status_code == 400
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/missions/test_match_api.py -v` — Expected: FAIL.

- [ ] **Step 3: Implement** `missions/apis/matching.py` — `MissionMatchApi.post`: `ensure_permission(request.user, Permission.MATCH_RUN)`; `mission = selectors.mission_get(mission_id)`; raise `ApplicationError` if `mission.status in {completed, cancelled}`; `Response(dataclasses.asdict(match_mission(mission)))`. URL: `missions/<int:mission_id>/match/`.

- [ ] **Step 4: Run tests, commit**

```bash
uv run pytest tests/ -v
git add -A && git commit -m "feat: match API"
```

---

### Task 5.3: Frontend — matcher dialog

**Files:**
- Create: `frontend/src/features/matching/api/matching.ts`, `frontend/src/features/matching/components/match-dialog.tsx`, `frontend/src/features/matching/matching.test.tsx`
- Modify: `frontend/src/features/assignments/components/staffing-panel.tsx` (add "Auto-match" button), `frontend/src/testing/mocks.ts`

**Interfaces:**
- Produces:
  - `features/matching/api/matching.ts`: `MatchResultSchema` mirroring `MatchResult` (team members with `seats`, `score`, `breakdown`, `soft_conflicts`; `unfilled_seats`; `alternatives`; `open_capacity`), `useRunMatch(missionId)` (mutation, POST `/missions/:id/match/`)
  - `match-dialog.tsx`: opened from the staffing panel (button visible with `match.run`, mission non-terminal). Flow: on open → run match → render:
    - team member cards: name, seat badges ("Piloting ≥7"), score, breakdown in a `Popover` (fit / workload / conflict penalty), amber chips for soft conflicts, checkbox (default checked)
    - per-requirement swap `Select` fed by `alternatives` — choosing an alternative unchecks the member currently covering that requirement and adds the alternative to the selection
    - unfilled seats: destructive-styled list "Piloting ≥9 — no qualified crew"
    - footer: "Propose N assignments" → `useProposeAssignments(missionId)` with the selected `user_ids` → invalidate staffing → close + `toast.success`; "Re-run" button
- Consumes: `useProposeAssignments` (Stage 4), `hasPermission`

- [ ] **Step 1: Write the failing test** — `matching.test.tsx`: mock `POST /api/v1/missions/10/match/` returning a two-member team + one unfilled seat + alternatives; render `/missions/10`, open Auto-match, assert both member names and the unfilled reason render; uncheck one member, click "Propose 1 assignments", assert the propose POST body contains only the checked `user_ids`. Run: `npm test -- --run` — Expected: FAIL.

- [ ] **Step 2: Implement** per Interfaces.

- [ ] **Step 3: Verify green + manual smoke, commit**

Manual: seeded org → mission with requirements → Auto-match → swap someone → propose → roster fills with proposed rows.

```bash
npm test -- --run && npm run build
git add -A && git commit -m "feat: matcher dialog with explanations, swaps, bulk propose"
```

---

**Stage 5 exit criteria:** suites green · matcher demonstrably picks generalists/balanced workloads (unit-proven) · infeasibility explained in UI · lead can go requirement → match → swap → propose → crew accepts → director approves, entirely in the product.
