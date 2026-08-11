# Stage 6: Dashboard & Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Global constraints in `00-overview.md` apply to every task.

**Goal:** The four dashboard metric groups (spec §13), the dashboard UI, a rich idempotent `seed_demo`, the README, and final delivery checks.

**Architecture:** Dashboard is read-only: four independent selector functions in `missions/selectors/dashboard.py`, one API, one page of widgets. Metrics use `date.today()` — tests build fixtures relative to today.

**Tech Stack:** See `00-overview.md`.

---

### Task 6.1: Dashboard selectors

**Files:**
- Create: `backend/mission_control/missions/selectors/dashboard.py`, `backend/tests/missions/test_dashboard.py`

**Interfaces:**
- Produces (`missions.selectors.dashboard`), all plain dict/list returning, all tenant-scoped via the models' scoped managers:
  - `pipeline_summary() -> dict` — `{"status_counts": {<each of the 7 statuses>: int}, "pending_approvals": [{"mission_id", "name", "submitted_at", "age_days"}], "upcoming": [{"mission_id", "name", "start_date", "days_until"}]}`. `submitted_at` = latest transition into `pending_approval`; `upcoming` = missions in draft/pending_approval/approved with `start_date` within `[today, today+30]`, soonest first.
  - `staffing_readiness() -> list[dict]` — for missions in pending_approval/approved/active with `end_date >= today`: `{"mission_id", "name", "status", "start_date", "coverage_pct" (filled seats / total seats × 100, 100 when no requirements), "accepted_count", "min_crew", "fully_covered", "at_risk"}` where `at_risk = not fully_covered or accepted_count < min_crew`; at-risk rows first, then by `start_date`.
  - `crew_utilization(window_days=90) -> dict` — window `[today, today+window_days)`; per active crew member, accepted assignment-days on approved/active missions clipped to the window: `{"window_days", "org_utilization_pct", "crew": [{"user_id", "name", "assigned_days", "utilization_pct"}]}` sorted most-loaded first (idle crew included with 0).
  - `skill_gaps() -> list[dict]` — per skill referenced by requirements of open missions (draft/pending_approval/approved/active, `end_date >= today`): `{"skill_id", "skill_name", "open_seats" (Σ required_count), "qualified_crew" (active crew with proficiency ≥ the skill's lowest required min_proficiency), "gap": open_seats > qualified_crew}`; gaps first, then by name.
- Consumes: `mission_coverage` (readiness), models

- [ ] **Step 1: Write the failing tests**

`backend/tests/missions/test_dashboard.py`:

```python
import datetime as dt

import pytest

from mission_control.missions.factories import (
    AssignmentFactory, MissionFactory, MissionRequirementFactory,
)
from mission_control.missions.models import AssignmentStatus, MissionStatus, MissionTransition
from mission_control.missions.selectors.dashboard import (
    crew_utilization, pipeline_summary, skill_gaps, staffing_readiness,
)
from mission_control.tenants.context import set_current_tenant_id
from mission_control.users.factories import CrewSkillFactory, SkillFactory, TenantFactory, UserFactory
from mission_control.users.roles import Role

pytestmark = pytest.mark.django_db
TODAY = dt.date.today()


@pytest.fixture
def tenant():
    t = TenantFactory()
    set_current_tenant_id(t.id)
    return t


def test_pipeline_counts_and_queue(tenant):
    lead = UserFactory(role=Role.MISSION_LEAD, tenant=tenant)
    MissionFactory(tenant=tenant, created_by=lead)  # draft
    pending = MissionFactory(tenant=tenant, created_by=lead, status=MissionStatus.PENDING_APPROVAL,
                             start_date=TODAY + dt.timedelta(days=10),
                             end_date=TODAY + dt.timedelta(days=20), name="Awaiting")
    MissionTransition.objects_unscoped.create(
        tenant=tenant, mission=pending, from_status="draft", to_status="pending_approval",
        actor=lead, reason="")
    summary = pipeline_summary()
    assert summary["status_counts"]["draft"] == 1
    assert summary["status_counts"]["pending_approval"] == 1
    assert summary["pending_approvals"][0]["name"] == "Awaiting"
    assert summary["pending_approvals"][0]["age_days"] == 0
    assert any(u["name"] == "Awaiting" for u in summary["upcoming"])


def test_readiness_flags_understaffed(tenant):
    lead = UserFactory(role=Role.MISSION_LEAD, tenant=tenant)
    mission = MissionFactory(tenant=tenant, created_by=lead, status=MissionStatus.APPROVED,
                             start_date=TODAY + dt.timedelta(days=5),
                             end_date=TODAY + dt.timedelta(days=10), min_crew=2, max_crew=4)
    skill = SkillFactory(tenant=tenant)
    MissionRequirementFactory(mission=mission, skill=skill, min_proficiency=5, required_count=2)
    crew = UserFactory(role=Role.CREW_MEMBER, tenant=tenant)
    CrewSkillFactory(user=crew, skill=skill, proficiency=8)
    AssignmentFactory(mission=mission, user=crew, status=AssignmentStatus.ACCEPTED)
    rows = staffing_readiness()
    assert rows[0]["coverage_pct"] == 50
    assert rows[0]["at_risk"] is True


def test_utilization_clips_to_window(tenant):
    crew = UserFactory(role=Role.CREW_MEMBER, tenant=tenant, name="Busy Bee")
    UserFactory(role=Role.CREW_MEMBER, tenant=tenant, name="Idle")
    mission = MissionFactory(tenant=tenant, status=MissionStatus.ACTIVE,
                             start_date=TODAY, end_date=TODAY + dt.timedelta(days=200))
    AssignmentFactory(mission=mission, user=crew, status=AssignmentStatus.ACCEPTED)
    data = crew_utilization(window_days=90)
    busy = next(c for c in data["crew"] if c["name"] == "Busy Bee")
    idle = next(c for c in data["crew"] if c["name"] == "Idle")
    assert busy["assigned_days"] == 90 and busy["utilization_pct"] == 100
    assert idle["assigned_days"] == 0
    assert data["org_utilization_pct"] == 50


def test_skill_gap_flagged(tenant):
    lead = UserFactory(role=Role.MISSION_LEAD, tenant=tenant)
    mission = MissionFactory(tenant=tenant, created_by=lead,
                             start_date=TODAY + dt.timedelta(days=5),
                             end_date=TODAY + dt.timedelta(days=10))
    scarce = SkillFactory(tenant=tenant, name="Xenobotany")
    MissionRequirementFactory(mission=mission, skill=scarce, min_proficiency=7, required_count=3)
    one_expert = UserFactory(role=Role.CREW_MEMBER, tenant=tenant)
    CrewSkillFactory(user=one_expert, skill=scarce, proficiency=9)
    gaps = skill_gaps()
    row = next(g for g in gaps if g["skill_name"] == "Xenobotany")
    assert row == {"skill_id": scarce.id, "skill_name": "Xenobotany",
                   "open_seats": 3, "qualified_crew": 1, "gap": True}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/missions/test_dashboard.py -v` — Expected: FAIL (module missing).

- [ ] **Step 3: Implement `missions/selectors/dashboard.py`**

```python
import datetime as dt
from collections import defaultdict

from django.db.models import Count

from mission_control.missions.models import (
    Assignment, AssignmentStatus, Mission, MissionStatus, MissionTransition,
)
from mission_control.missions.selectors.staffing import mission_coverage
from mission_control.tenants.context import require_current_tenant_id
from mission_control.users.models import CrewSkill, User
from mission_control.users.roles import Role

OPEN_STATUSES = frozenset({MissionStatus.DRAFT, MissionStatus.PENDING_APPROVAL,
                           MissionStatus.APPROVED, MissionStatus.ACTIVE})


def pipeline_summary() -> dict:
    today = dt.date.today()
    counts = {status: 0 for status in MissionStatus.values}
    for row in Mission.objects.values("status").annotate(n=Count("id")):
        counts[row["status"]] = row["n"]

    pending = []
    for mission in Mission.objects.filter(status=MissionStatus.PENDING_APPROVAL):
        submitted = (MissionTransition.objects.filter(
            mission=mission, to_status=MissionStatus.PENDING_APPROVAL)
            .order_by("-created_at").first())
        submitted_at = submitted.created_at if submitted else mission.created_at
        pending.append({"mission_id": mission.id, "name": mission.name,
                        "submitted_at": submitted_at,
                        "age_days": (today - submitted_at.date()).days})
    pending.sort(key=lambda p: -p["age_days"])

    upcoming = [
        {"mission_id": m.id, "name": m.name, "start_date": m.start_date,
         "days_until": (m.start_date - today).days}
        for m in Mission.objects.filter(
            status__in=[MissionStatus.DRAFT, MissionStatus.PENDING_APPROVAL, MissionStatus.APPROVED],
            start_date__gte=today, start_date__lte=today + dt.timedelta(days=30),
        ).order_by("start_date")
    ]
    return {"status_counts": counts, "pending_approvals": pending, "upcoming": upcoming}


def staffing_readiness() -> list[dict]:
    today = dt.date.today()
    rows = []
    missions = Mission.objects.filter(
        status__in=[MissionStatus.PENDING_APPROVAL, MissionStatus.APPROVED, MissionStatus.ACTIVE],
        end_date__gte=today,
    ).prefetch_related("requirements__skill")
    for mission in missions:
        report = mission_coverage(mission)
        total = sum(c.required_count for c in report.requirements)
        filled = sum(min(c.filled_count, c.required_count) for c in report.requirements)
        coverage_pct = round(100 * filled / total) if total else 100
        at_risk = not report.fully_covered or report.accepted_count < mission.min_crew
        rows.append({"mission_id": mission.id, "name": mission.name, "status": mission.status,
                     "start_date": mission.start_date, "coverage_pct": coverage_pct,
                     "accepted_count": report.accepted_count, "min_crew": mission.min_crew,
                     "fully_covered": report.fully_covered, "at_risk": at_risk})
    rows.sort(key=lambda r: (not r["at_risk"], r["start_date"]))
    return rows


def crew_utilization(window_days: int = 90) -> dict:
    today = dt.date.today()
    window_end = today + dt.timedelta(days=window_days - 1)
    days = defaultdict(int)
    assignments = Assignment.objects.filter(
        status=AssignmentStatus.ACCEPTED,
        mission__status__in=[MissionStatus.APPROVED, MissionStatus.ACTIVE],
        mission__start_date__lte=window_end, mission__end_date__gte=today,
    ).select_related("mission")
    for a in assignments:
        start = max(a.mission.start_date, today)
        end = min(a.mission.end_date, window_end)
        days[a.user_id] += (end - start).days + 1

    crew = list(User.objects.filter(
        tenant_id=require_current_tenant_id(), role=Role.CREW_MEMBER, is_active=True))
    rows = [{"user_id": u.id, "name": u.name, "assigned_days": days.get(u.id, 0),
             "utilization_pct": round(100 * days.get(u.id, 0) / window_days)} for u in crew]
    rows.sort(key=lambda r: (-r["assigned_days"], r["name"]))
    org = round(sum(r["utilization_pct"] for r in rows) / len(rows)) if rows else 0
    return {"window_days": window_days, "org_utilization_pct": org, "crew": rows}


def skill_gaps() -> list[dict]:
    today = dt.date.today()
    requirement_rows = (
        Mission.objects.filter(status__in=OPEN_STATUSES, end_date__gte=today)
        .values_list("requirements__skill_id", "requirements__skill__name",
                     "requirements__min_proficiency", "requirements__required_count")
    )
    seats = defaultdict(int)
    min_prof = {}
    names = {}
    for skill_id, name, prof, count in requirement_rows:
        if skill_id is None:
            continue
        seats[skill_id] += count
        names[skill_id] = name
        min_prof[skill_id] = min(min_prof.get(skill_id, 11), prof)

    gaps = []
    for skill_id, open_seats in seats.items():
        qualified = CrewSkill.objects.filter(
            skill_id=skill_id, proficiency__gte=min_prof[skill_id],
            user__role=Role.CREW_MEMBER, user__is_active=True,
        ).values("user_id").distinct().count()
        gaps.append({"skill_id": skill_id, "skill_name": names[skill_id],
                     "open_seats": open_seats, "qualified_crew": qualified,
                     "gap": open_seats > qualified})
    gaps.sort(key=lambda g: (not g["gap"], g["skill_name"]))
    return gaps
```

- [ ] **Step 4: Run tests, commit**

```bash
uv run pytest tests/missions/test_dashboard.py -v
git add -A && git commit -m "feat: dashboard selectors — pipeline, readiness, utilization, skill gaps"
```

---

### Task 6.2: Dashboard API + UI

**Files:**
- Create: `backend/mission_control/missions/apis/dashboard.py`, `backend/tests/missions/test_dashboard_api.py`, `frontend/src/features/dashboard/api/dashboard.ts`, `frontend/src/features/dashboard/components/dashboard-page.tsx`, `frontend/src/features/dashboard/dashboard.test.tsx`
- Modify: `backend/mission_control/missions/urls.py`, `frontend/src/app/router.tsx` (HomeRedirect renders `<DashboardPage/>`), `frontend/src/testing/mocks.ts`

**Interfaces:**
- Produces:
  - `GET /api/v1/dashboard/` (perm `dashboard.view`) → `{"pipeline": pipeline_summary(), "readiness": staffing_readiness(), "utilization": crew_utilization(), "skill_gaps": skill_gaps()}`
  - `features/dashboard/api/dashboard.ts`: `DashboardSchema` mirroring the payload, `useDashboard()` (key `["dashboard"]`)
  - `dashboard-page.tsx`: four cards — **Pipeline** (status count chips; pending-approval list with age badges, each linking to the mission; upcoming list), **Staffing readiness** (rows with coverage bar, at-risk rows highlighted destructive, links to missions), **Crew utilization** (org % headline; top-5 and bottom-5 lists), **Skill gaps** (table; gap rows flagged). Crew-member redirect behaviour from Stage 1 unchanged.
- Backend test: director gets 200 with all four keys; crew member gets 403. Frontend test: renders mocked payload — asserts a status chip, an at-risk mission name, org utilization %, and a gap row.

- [ ] **Step 1: Write both failing tests** (shapes above). Run backend + frontend suites — Expected: FAIL.

- [ ] **Step 2: Implement** API (one view, four selector calls) and page per Interfaces.

- [ ] **Step 3: Verify green, commit**

```bash
uv run pytest tests/ -v && cd ../frontend && npm test -- --run && npm run build
git add -A && git commit -m "feat: org dashboard with pipeline, readiness, utilization, skill gaps"
```

---

### Task 6.3: Full seed, README, delivery checks

**Files:**
- Modify: `backend/mission_control/users/management/commands/seed_demo.py`, `backend/tests/users/test_seed.py`
- Create: `README.md`, `backend/tests/test_rbac_matrix.py`

**Interfaces:**
- Produces: a demo environment where every screen has meaningful data on first login, and a README that gets an evaluator from clone → running product in three commands.

- [ ] **Step 1: Extend `seed_demo`**

Keep it idempotent: users/skills via `get_or_create`-style guards; missions guarded by `if Mission.objects_unscoped.filter(tenant=tenant).exists(): continue`. Per tenant (Helios full-size, Meridian smaller):

- Skills (8): Piloting, Navigation, EVA Ops, Life Support, Robotics, Geology, Comms, Medicine (+1 archived: "Legacy Telemetry").
- Crew: 15 for Helios / 8 for Meridian — `crew1..crewN@<slug>.test`, each with 2–4 `CrewSkill`s assigned deterministically (`skills[(i + j) % len(skills)]`, proficiency `3 + (i * 2 + j) % 8`) — varied but reproducible, no `random`.
- Missions, dates relative to `date.today()` (so FSM guards hold):
  - draft "Callisto Flyby Prep" (starts +40d), requirements set, no assignments
  - pending_approval "Ganymede Survey" (starts +14d) — staffed with accepted crew, `submit` transition row (age for the queue)
  - pending_approval "Europa Ice Core" (starts +16d, **overlapping crew member with Ganymede Survey** — the soft-conflict showcase)
  - approved "Titan Relay Deploy" (starts +7d) — fully staffed, submit+approve transition rows
  - active "Orbital Debris Sweep" (started −3d, ends +4d) — accepted crew, full transition history
  - completed "Solar Array Refit" (−30d → −20d)
  - rejected "Asteroid Prospecting" — reject transition with reason "Budget window closed"
  - cancelled "Deep Space Antenna" — cancel transition, assignments removed
  - plus one draft with a `declined` assignment (decline_reason "Family commitments") and one `proposed` awaiting `crew1`'s response — so `crew1@helios-aerospace.test`'s my-assignments page has all three groups populated.
- Update `tests/users/test_seed.py`:

```python
def test_seed_demo_idempotent():
    call_command("seed_demo")
    call_command("seed_demo")
    assert Tenant.objects.count() == 2
    assert User.objects.filter(email="director@helios-aerospace.test").exists()
    from mission_control.missions.models import Mission, MissionStatus
    helios = Tenant.objects.get(slug="helios-aerospace")
    statuses = set(Mission.objects_unscoped.filter(tenant=helios).values_list("status", flat=True))
    assert statuses == set(MissionStatus.values)
    assert User.objects.filter(tenant=helios).count() >= 17  # director + lead + 15 crew
```

Run: `uv run pytest tests/users/test_seed.py -v` — Expected: PASS after implementation.

- [ ] **Step 1b: Add the parametrized RBAC matrix (spec §14)**

`backend/tests/test_rbac_matrix.py` — one table asserting every role's access to every permission-gated GET endpoint:

```python
import pytest

from mission_control.users.factories import UserFactory

pytestmark = pytest.mark.django_db

CASES = [
    ("/api/v1/missions/", {"director": 200, "mission_lead": 200, "crew_member": 403}),
    ("/api/v1/crew/", {"director": 200, "mission_lead": 200, "crew_member": 403}),
    ("/api/v1/skills/", {"director": 200, "mission_lead": 200, "crew_member": 200}),
    ("/api/v1/settings/users/", {"director": 200, "mission_lead": 403, "crew_member": 403}),
    ("/api/v1/settings/organisation/", {"director": 200, "mission_lead": 403, "crew_member": 403}),
    ("/api/v1/dashboard/", {"director": 200, "mission_lead": 200, "crew_member": 403}),
    ("/api/v1/me/assignments/", {"director": 403, "mission_lead": 403, "crew_member": 200}),
    ("/api/v1/me/skills/", {"director": 403, "mission_lead": 403, "crew_member": 200}),
]


@pytest.mark.parametrize("url,expectations", CASES)
def test_rbac_matrix(auth_client_for, url, expectations):
    for role, expected in expectations.items():
        user = UserFactory(role=role)
        assert auth_client_for(user).get(url).status_code == expected, f"{role} GET {url}"
```

Run: `uv run pytest tests/test_rbac_matrix.py -v` — Expected: PASS (write-path RBAC is already covered per-endpoint in Stages 2–5).

- [ ] **Step 2: Write `README.md`**

Sections: what it is (one paragraph + screenshot placeholder-free feature list) · Quickstart (`docker compose -f docker-compose.dev.yml up` → http://localhost:5173; prod: `docker compose up` → http://localhost:80) · Demo credentials table (all six users + `orbit-demo-2026`, and `crew1@helios-aerospace.test` called out as the interesting crew login) · Suggested demo tour (lead: mission → requirements → auto-match → propose; crew: accept; director: approve; dashboard) · Architecture overview (stack, four apps, tenancy guardrails summary, FSM diagram from spec §8, matcher summary — link to `docs/superpowers/specs/2026-08-11-mission-control-design.md`) · Running tests (`cd backend && uv run pytest` / `cd frontend && npm test -- --run`) · Repo layout.

- [ ] **Step 3: Delivery checks**

```bash
cd backend && uv run ruff check . && uv run pytest
cd ../frontend && npm run lint && npm test -- --run && npm run build
docker compose up --build -d && sleep 10
curl -s -o /dev/null -w "%{http_code}" http://localhost:80   # expect 200
curl -s http://localhost:80/api/v1/auth/me/ | head -c 200    # expect the 401 envelope JSON
docker compose down
```

Also verify by hand in the prod stack: login each role; every list page shows data or a designed empty state; cross-role nav is correctly gated.

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "feat: full demo seed, README, delivery checks"
```

---

**Stage 6 / project exit criteria:** CI green · both suites green · prod compose serves the seeded product on :80 · dashboard populated for both tenants · README quickstart verified from a clean checkout · demo tour (match → propose → accept → approve → activate) works end-to-end.
