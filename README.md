# Mission Control

Mission Control is a multi-tenant crew-staffing tool for an organisation running discrete "missions"
(expeditions, deployments, projects — the domain is deliberately generic). A mission lead defines a
mission's skill requirements, proposes crew against them (by hand or via an auto-matcher), crew accept
or decline, a director reviews and approves before the mission goes live, and a dashboard tracks the
whole pipeline: which missions are under-staffed, who's overloaded, and where the organisation is short
on a skill it keeps needing.

**What it does, concretely:**

- **Tenancy.** Every organisation ("tenant") sees only its own data. Enforced at the database level, not
  just in application code — see [Architecture](#architecture-in-brief) below.
- **Users, roles and a 16-permission catalog.** Three roles (director, mission lead, crew member), each a
  fixed set of the 16 permissions. JWT auth, access token in memory, rotating refresh token.
- **Skills & crew.** An organisation-wide skill catalog (with archiving); each crew member declares their
  own proficiency (1–10) per skill.
- **Missions with a seven-state lifecycle.** `draft → pending_approval → approved → active → completed`,
  with `rejected`/`revise` and `cancel` branches, each transition permission-gated, guarded (e.g. "can't
  approve an under-staffed mission"), and audited.
- **Assignments with a real availability rule.** Crew are proposed, and accept or decline. An *accepted*
  assignment on an *approved or active* mission hard-blocks that person for the overlapping dates
  everywhere else; any other overlap is a non-blocking soft-conflict warning.
- **An auto-matching engine.** Given a mission's requirements, proposes a scored, explainable team —
  balancing skill fit, workload, and conflicts — with reasons for any seat it can't fill.
- **An organisation dashboard.** Pipeline funnel, staffing readiness for live missions, crew utilisation,
  and skill supply-vs-demand gaps.

## Quickstart

**Prerequisites:** git and Docker with Compose v2 (Docker Desktop on macOS/Windows, or Docker Engine +
the compose plugin on Linux). Nothing else — both stacks run entirely in containers, so no local
Python/Node toolchain is needed to get the app up. (You only need [`uv`](https://docs.astral.sh/uv/) and
Node 22+ if you want to run tests or `manage.py` commands outside Docker — see
[Running tests](#running-tests).)

```bash
git clone https://github.com/srichards2103/mission-control.git
cd mission-control
```

### Dev stack (fastest path)

Hot-reload everything: Postgres + Django dev server + Vite. **No `.env` file or environment variables
are required** — the dev compose file carries safe defaults for everything.

```bash
docker compose -f docker-compose.dev.yml up
```

Open **http://localhost:5173** and log in with any account from
[Demo credentials](#demo-credentials) — e.g. `director@helios-aerospace.test` / `orbit-demo-2026`.
The backend container runs migrations and `seed_demo` automatically before starting the dev server, so
the app is fully populated the first time it comes up.

### Prod stack

Built SPA behind nginx, gunicorn, migrations + seed on boot. This stack requires one environment
variable, `SECRET_KEY`; the supported way to provide it is a `.env` file next to `docker-compose.yml`
(Compose auto-loads it):

```bash
cp .env.example .env
# then edit .env and set:
#   SECRET_KEY=<any long random string>        # required — e.g. `openssl rand -hex 32`
#   ALLOWED_HOSTS=localhost,127.0.0.1          # optional — defaults to this; set real domain(s) in a deploy
docker compose up --build
```

Or inline, without a `.env` file:

```bash
SECRET_KEY=$(openssl rand -hex 32) docker compose up --build
```

Open **http://localhost:80**. `docker-compose.yml` fails closed without `SECRET_KEY` set — this is
deliberate, so a production-shaped stack can never boot on a known, publicly-committed placeholder key.

Both compose files provision Postgres 16, wait for its healthcheck, then run `migrate` and `seed_demo`
before serving. Re-running either command is safe: the seed is idempotent. (A separate
[`backend/.env.example`](backend/.env.example) exists only for running the Django backend directly on
your machine, outside Docker — not needed for either compose flow.)

Only `SECRET_KEY` fails closed — the Postgres credentials (`mission`/`mission`) are hardcoded in both
compose files with no override path. Exposure is low: the prod `db` service publishes no host port, so
it's reachable only from other containers on the compose network, not from the host or outside.

To seed by hand against an already-running stack (e.g. after wiping the database), run the same command
the containers run:

```bash
cd backend && uv run python manage.py migrate && uv run python manage.py seed_demo
```

## Demo credentials

All accounts share the password **`orbit-demo-2026`**. Logins are by email; every account also has a
realistic display name (e.g. `crew1@helios-aerospace.test` appears in the UI as **Amara Okafor**,
`lead@helios-aerospace.test` as **Marcus Hale**, `director@helios-aerospace.test` as **Rosa Delgado**).

| Tenant | Email | Role |
|---|---|---|
| Helios Aerospace | `director@helios-aerospace.test` | Director |
| Helios Aerospace | `lead@helios-aerospace.test` | Mission Lead |
| Helios Aerospace | **`crew1@helios-aerospace.test`** | Crew Member — see below |
| Helios Aerospace | `crew2`–`crew15@helios-aerospace.test` | Crew Member |
| Meridian Orbital | `director@meridian-orbital.test` | Director |
| Meridian Orbital | `lead@meridian-orbital.test` | Mission Lead |
| Meridian Orbital | `crew1`–`crew8@meridian-orbital.test` | Crew Member |

**`crew1@helios-aerospace.test`** is the interesting crew login: their **My Assignments** page has all
three groups populated at once — an accepted upcoming assignment (*Ganymede Survey*), a proposal still
awaiting a response (*Europa Ice Core*), and a declined one in their history (*Vesta Sample Return*,
declined with reason "Family commitments").

Log in as each tenant's director to see that the two organisations' data never mixes — different
missions, different crew, different dashboard numbers, same login page.

## Suggested demo tour

Everything below happens in the **Helios Aerospace** tenant unless noted.

1. **As `lead@helios-aerospace.test`** — open **Callisto Flyby Prep** (draft). It already has skill
   requirements (EVA Ops ≥7 ×3, Geology ≥5 ×1) and no crew yet. Open the **Auto-match** dialog: the
   matcher proposes a ranked team with score breakdowns, and reports the EVA Ops seat it can't fully
   fill — the organisation genuinely doesn't have three EVA Ops-qualified people (see the dashboard's
   skill-gap card for the same shortfall). Propose a candidate from the match result.
2. Open **Ganymede Survey** (pending_approval). Its roster shows both conflict treatments side by side:
   one crew member with an amber "Conflict" indicator (a soft, non-blocking overlap with *Europa Ice
   Core*, also pending) and one with a red "Unavailable" indicator (a hard block — they're also accepted
   on the now-approved *Titan Relay Deploy*, which overlaps in dates). Try **Approve** as
   `director@helios-aerospace.test` — the staffing guard refuses it, with reasons.
3. **As `crew1@helios-aerospace.test`** — go to **My Assignments**. Accept or decline the pending
   *Europa Ice Core* proposal; see the existing accepted and declined entries in the other two groups.
4. **As `director@helios-aerospace.test`** — approve a properly-staffed mission (*Titan Relay Deploy* is
   already approved; try the pending pair once staffed, or watch *Orbital Debris Sweep*'s full history —
   submit → approve → activate — on its transition timeline).
5. Open the **Dashboard** as director or lead: the pipeline card shows missions spread across all seven
   states, the staffing-readiness list flags *Ganymede Survey* as at-risk, crew utilisation shows real
   variation, and the skill-gap card lists EVA Ops as short.

## Architecture in brief

**Stack:** Django + Django REST Framework + PostgreSQL on the backend (HackSoft-style: services for
writes, selectors for reads, thin `APIView`s with inline serializers); React + Vite + TypeScript +
TanStack Query + zod on the frontend (bulletproof-react feature folders). JWT auth
(`djangorestframework-simplejwt`) with access token in memory and a rotating refresh token in
`localStorage`. Full design rationale, data model, and every endpoint's contract are in
[`docs/superpowers/specs/2026-08-11-mission-control-design.md`](docs/superpowers/specs/2026-08-11-mission-control-design.md).

**Four Django apps only**, one-way dependency `missions → users → tenants → common`. Matching and the
dashboard are modules inside `missions` (services/selectors), not apps of their own.

```
backend/mission_control/
  common/     # BaseModel, pagination, exception handler
  tenants/    # Tenant, tenant context (contextvars), TenantModel + scoped managers
  users/      # User, roles, 16-permission catalog, Skill, CrewSkill, auth
  missions/   # Mission, MissionTransition, MissionRequirement, Assignment
              #   services/  (writes: FSM transitions, assignments, matcher)
              #   selectors/ (reads: staffing/availability, dashboard aggregates)
              #   apis/      (one module per API group)
frontend/src/
  app/            # router, providers
  components/ui/  # shadcn primitives
  features/       # auth, missions, crew, skills, assignments, matching, dashboard, settings, profile
  lib/            # axios client + interceptors, auth/permission hook
```

**Tenancy guardrails, summarised:** every tenant-scoped model's default manager filters by a tenant id
held in a Python `contextvar` and **raises rather than returns unscoped data** if no tenant is set — a
missing tenant fails closed, it never silently shows everything. That context is populated per-request
from the authenticated user's own `tenant_id` (never from anything client-supplied), so it can't be
spoofed. Cross-tenant lookups return 404, never 403 — a mission that belongs to another tenant simply
doesn't exist as far as your request is concerned. Composite `(tenant_id, id)` foreign keys make
cross-tenant data association a database constraint violation, not just an application bug.

**Mission lifecycle (FSM):**

```
draft ─submit─▶ pending_approval ─approve─▶ approved ─activate─▶ active ─complete─▶ completed
  ▲                    │
  └──revise── rejected ◀─reject─┘
cancelled ◀─cancel─ (any non-terminal state)
```

Every transition runs in one function — permission check → object-level rule (no self-approval; leads
only manage their own missions) → state validity → domain guard (e.g. `approve` requires full staffing
coverage and no crew conflicts; `activate` requires the start date has arrived) → status write + an
audit row, atomically.

**Matching engine, summarised:** a greedy weighted set-cover over a mission's unfilled requirement seats.
Each candidate is scored on skill-proficiency fit above the minimum, workload balance (less-booked people
score higher), and a soft-conflict penalty; any seat it can't fill comes back with one of four fixed
reasons (no qualified crew at all / all qualified crew unavailable / `max_crew` too small / not enough
qualified crew). It never writes anything — a lead reviews the proposal and proposes for real.

## Running tests

```bash
# Backend: pytest + pytest-django + factory_boy, against PostgreSQL
cd backend && uv run pytest

# Frontend: vitest + Testing Library + MSW
cd frontend && npm test -- --run
```

Linting: `cd backend && uv run ruff check .` and `cd frontend && npm run lint` (oxlint). Production build:
`cd frontend && npm run build`.

## Repo layout

```
backend/                  # Django + DRF API — see mission_control/ above
frontend/                 # React SPA — see src/ above
docker-compose.dev.yml    # Postgres + Django dev server + Vite (hot reload, proxy /api)
docker-compose.yml        # Postgres + gunicorn + nginx (built SPA, /api proxy), fails closed on secrets
docs/superpowers/specs/   # Design spec (source of truth for behaviour not covered here)
docs/reviewer-notes.md    # How this was built (process), plus known loose ends
docs/transcripts/         # Claude Code session transcripts (readable .md renders + raw .jsonl)
```

## Known limitations

Recorded here rather than left for a reviewer to discover:

- **List screens are not paginated in the UI.** The API paginates every list
  (`{"results": [...], "count": n, "limit": n, "offset": n}`), but the frontend's list hooks fetch with a
  hardcoded `limit: 100` and use only `.results`, discarding `count`. A tenant with more than 100 crew,
  missions, or skills will see that list silently truncated at 100 — there's no "load more" or page
  control. None of the seeded demo data hits this ceiling.
- **The dashboard's staffing-readiness query is `1 + 3N`, not constant.** `staffing_readiness()` in
  `backend/mission_control/missions/selectors/dashboard.py` calls `mission_coverage()` once per
  currently-live mission (pending_approval/approved/active, not yet ended), each of which is a bounded
  handful of queries — so the total is linear in the number of live missions rather than O(1). At the
  seeded demo's scale (a handful of live missions per tenant) this is unnoticeable; at real scale it
  would need a batched `mission_coverage_batch()` added to `selectors/staffing.py`. The dashboard's other
  three widgets (pipeline, crew utilisation, skill gaps) are all genuinely O(1).
- **`GET /missions/` doesn't implement the date-range filter spec §11 promises.** The spec lists the
  filters as "status, date range, search"; only `status` and `search` exist on the selector
  (`mission_control/missions/selectors/missions.py`), and even `search` has no UI control feeding it —
  it's reachable only by calling the API directly. Adding a date-range filter plus its UI is beyond this
  plan's scope, consistent with the pagination limitation above: disclosed here rather than implemented.

Two further product-level loose ends — skill edits after assignment ("skill drift") and the lack of a
crew-facing warning when accepting an overlapping proposal — are analysed in
[`docs/reviewer-notes.md`](docs/reviewer-notes.md), alongside notes on how this codebase was built.

None of the above is hidden from the codebase: `staffing_readiness()`'s docstring measures its own query
count and the frontend list hooks are consistent (not accidental) across every list screen.
