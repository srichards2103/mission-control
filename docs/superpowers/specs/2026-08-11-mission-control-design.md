# Mission Control — Design Spec

**Date:** 2026-08-11
**Status:** Approved for implementation planning
**Inputs:** `project-brief.md` (challenge brief), `initial-brief.md` (direction & constraints)

Mission Control is a multi-tenant B2B platform for space organisations: mission planning with an
approval lifecycle, crew skill profiles, an auto-matching engine that assembles teams, and an
org-level dashboard. This spec records the agreed design; the implementation plan derives from it.

---

## 1. Key decisions

| Decision | Choice | Rationale |
|---|---|---|
| Multi-tenancy | Single database, shared schema, tenant FK + fail-closed scoped managers | Simplest to operate; safety comes from layered guardrails (§4) |
| Assignment model | Crew accept/decline proposals | Project brief: crew "respond to assignments"; gives crew role a real workflow |
| Availability | Accepted assignments on **approved/active** missions hard-block; everything else is a soft conflict | First-approved wins; approved missions can never lose crew silently; drafts can plan freely |
| Mission lifecycle | Seven-state FSM (§8) | `approved` ≠ `active` is load-bearing for the availability model |
| Matcher | Greedy weighted set-cover team builder with explanations | Solves the real combinatorial problem, deterministic, explainable in UI |
| Auth | JWT (djangorestframework-simplejwt), access + rotating refresh | User choice; local auth per brief, seeded users |
| Roles/permissions | 3 role enums inheriting from a 16-permission catalog | Changing a role's scope = editing a permission set, not code |
| Dashboard | Pipeline, staffing readiness, crew utilization, skill supply/demand | All four selected |

## 2. Tech stack & conventions

- **Backend:** Django + DRF, PostgreSQL. [HackSoft style guide](https://github.com/HackSoftware/Django-Styleguide):
  `APIView`s with inline serializers, one service/selector call per API, all writes in `services.py`,
  all reads in `selectors.py`, `ApplicationError` + global exception handler.
- **Frontend:** React + Vite + TypeScript, shadcn/ui, TanStack Query, zod (every API response parsed),
  [bulletproof-react](https://github.com/alan2207/bulletproof-react) feature-driven structure.
- **Delivery:** Docker Compose (dev + prod), GitHub Actions CI (ruff + pytest; tsc + eslint + vitest + build).

## 3. Architecture

```
backend/
  config/                     # settings (django-environ), urls, wsgi
  mission_control/
    common/                   # BaseModel, pagination, exception handler, utils
    tenants/                  # Tenant, tenant context, TenantModel + scoped managers
    users/                    # User, Role enum, permission catalog, authz service, Skill, CrewSkill
    missions/
      models.py               # Mission, MissionTransition, MissionRequirement, Assignment
      services/               # missions.py, assignments.py, matching.py
      selectors/              # missions.py, staffing.py, dashboard.py
      apis/                   # one module per API group, inline serializers
frontend/
  src/
    app/                      # router, providers, route composition
    components/ui/            # shadcn primitives
    features/                 # auth, missions, crew, skills, assignments, matching, dashboard, settings
    lib/                      # api client (axios + interceptors), authz hook, utils
docker-compose.dev.yml        # postgres + runserver + vite (proxy /api)
docker-compose.yml            # postgres + gunicorn + nginx (built SPA, /api proxy)
```

Four Django apps only. Dependency direction is strictly one-way: `missions → users → tenants → common`.
Skills live in `users` because they describe crew capability independent of any mission. Matching and
dashboard are services/selectors inside `missions` — they own no models, so they are not apps.

## 4. Multi-tenancy guardrails

Four fail-closed layers:

1. **Tenant context** — a `contextvars.ContextVar` holding the current tenant id. JWT auth resolves in
   the DRF layer, so the context is set by a custom simplejwt authentication class immediately after
   token → user resolution. Middleware guarantees the context is cleared after every request,
   including on exceptions.
2. **Scoped managers** — abstract `TenantModel(BaseModel)` with `tenant = FK(Tenant, on_delete=PROTECT)`.
   The default manager filters every queryset by the context tenant and stamps `tenant` on create.
   With no tenant in context it **raises** (never returns unscoped data). `objects_unscoped` exists for
   migrations/admin/tests only.
3. **Service-layer validation** — services assert that related objects (mission ↔ skill,
   assignment ↔ user) share a tenant before writing.
4. **Database hardening** — `UNIQUE(tenant_id, id)` on parent tables plus composite FKs
   `(tenant_id, <parent>_id)` on `CrewSkill`, `MissionRequirement`, `Assignment` via `RunSQL`
   migrations. Cross-tenant links are physically impossible at the DB level.

Cross-tenant API access returns **404** (not 403) — existence of other tenants' records is never leaked.

## 5. Auth & error handling

- simplejwt: short-lived access token, rotating refresh token with blacklist.
- Frontend: access token in memory; refresh token in `localStorage`; axios interceptor refreshes once
  on 401 and retries, then logs out on failure.
- `GET /auth/me/` returns the user, role, and computed permission list — the frontend's single source
  of authz truth.
- Global exception handler (HackSoft pattern) maps `ApplicationError(message, extra)`, DRF
  `ValidationError`, `PermissionDenied`, and `NotFound` to one envelope: `{"message": str, "extra": {...}}`.

## 6. Data model

All tenant-scoped models inherit `TenantModel` (tenant FK, `created_at`, `updated_at`). Integer PKs.
Dates are day-granularity (`DateField`) — availability's unit is the day.

| Model | Fields & constraints |
|---|---|
| `Tenant` | `name`, `slug` (unique) |
| `User` | Custom user. `email` (globally unique, login), `name`, `tenant` FK, `role` ∈ {`DIRECTOR`, `MISSION_LEAD`, `CREW_MEMBER`}, `is_active`. **Exception:** keeps a standard manager (auth resolves email → user before tenant context exists); user-listing selectors scope by tenant explicitly. |
| `Skill` | `name`, `description`, `is_archived`. Unique `(tenant, lower(name))`. Archived skills remain valid on existing rows; new profiles/requirements cannot reference them. |
| `CrewSkill` | `user` FK, `skill` FK, `proficiency` (DB check `1..10`), unique `(user, skill)`. |
| `Mission` | `name`, `description`, `start_date`, `end_date`, `status`, `min_crew`, `max_crew`, `created_by` FK. DB checks: `end_date >= start_date`, `1 <= min_crew <= max_crew`. Fields other than `status` editable only in `draft`/`rejected` (service-enforced). |
| `MissionTransition` | Append-only: `mission` FK, `from_status`, `to_status`, `actor` FK, `reason`, `created_at`. Audit trail; rejection reasons and approval-queue aging derive from here. |
| `MissionRequirement` | `mission` FK, `skill` FK, `min_proficiency` (`1..10`), `required_count` (`>=1`), unique `(mission, skill, min_proficiency)`. "One pilot ≥9 and two pilots ≥5" = two rows. |
| `Assignment` | `mission` FK, `user` FK, `status` ∈ {`proposed`, `accepted`, `declined`, `removed`}, `decline_reason`, `created_by` FK, `responded_at`. **Partial unique index** on `(mission, user)` where status ∈ {`proposed`, `accepted`} — one live assignment per person per mission; declined/removed rows persist as history and re-proposing creates a fresh row. |

## 7. RBAC

### Permission catalog (16)

| Group | Permissions |
|---|---|
| Missions | `MISSION_VIEW`, `MISSION_CREATE`, `MISSION_EDIT`, `MISSION_PROGRESS` (submit/revise/activate/complete/cancel), `MISSION_REVIEW` (approve/reject) |
| Assignments | `ASSIGNMENT_MANAGE` (propose/remove), `ASSIGNMENT_RESPOND` (accept/decline own) |
| Matching | `MATCH_RUN` |
| People | `CREW_VIEW`, `USER_MANAGE` (create users with role, change role, deactivate) |
| Skills | `SKILL_VIEW`, `SKILL_MANAGE`, `OWN_SKILLS_EDIT` |
| Settings | `SETTINGS_VIEW` (settings area), `SETTINGS_MANAGE` (org-level edits) |
| Dashboard | `DASHBOARD_VIEW` |

### Role → permission sets (data, not code)

- **Director** — everything except `ASSIGNMENT_RESPOND`, `OWN_SKILLS_EDIT` (directors are not assignable crew).
- **Mission Lead** — `MISSION_VIEW/CREATE/EDIT/PROGRESS`, `ASSIGNMENT_MANAGE`, `MATCH_RUN`,
  `CREW_VIEW`, `SKILL_VIEW`, `DASHBOARD_VIEW`.
- **Crew Member** — `SKILL_VIEW`, `OWN_SKILLS_EDIT`, `ASSIGNMENT_RESPOND`. Mission visibility only
  through own assignments (nested payloads) — no org-wide mission list.

### Object-level invariants (service-enforced, not permissions)

1. A reviewer may never approve/reject a mission they created **or** submitted — including directors.
2. Leads may edit/progress only missions they created; directors, any mission.
3. `ASSIGNMENT_RESPOND` applies only to the caller's own assignments.

Enforcement: backend raises `PermissionDenied` via an authz service (`ensure(user, PERM)` + object
checks in services). Frontend gates routes (`<RequirePermission>`) and conditional UI (`useAuthz`)
from the `/auth/me/` permission list. Backend is authoritative.

## 8. Mission lifecycle (FSM)

```
draft ─submit─▶ pending_approval ─approve─▶ approved ─activate─▶ active ─complete─▶ completed
  ▲                    │
  └──revise── rejected ◀─reject─┘
cancelled ◀─cancel─ (any non-terminal state)
```

Implemented as a transition table in `missions/services/missions.py`; one service
`transition_mission(actor, mission, action, reason=None)` executes atomically:
**permission check → object-level rules → state validity → domain guards → write status + `MissionTransition` row**.

| Action | From → To | Permission | Guards |
|---|---|---|---|
| `submit` | draft → pending_approval | `MISSION_PROGRESS` | ≥ 1 requirement exists |
| `approve` | pending_approval → approved | `MISSION_REVIEW` | Not creator/submitter. Staffing validation: every requirement covered by accepted assignments (§9 coverage), accepted count ∈ `[min_crew, max_crew]`, no accepted member hard-blocked by an overlapping approved/active mission. Runs in a transaction with row locks on affected assignments so concurrent competing approvals cannot both succeed. |
| `reject` | pending_approval → rejected | `MISSION_REVIEW` | Not creator/submitter; reason required |
| `revise` | rejected → draft | `MISSION_PROGRESS` | — |
| `activate` | approved → active | `MISSION_PROGRESS` | `start_date <= today`; re-runs conflict check (belt and braces) |
| `complete` | active → completed | `MISSION_PROGRESS` | `end_date <= today` |
| `cancel` | any non-terminal → cancelled | `MISSION_PROGRESS` | Reason required; live assignments flip to `removed` |

Activation and completion are explicit actions; the UI nudges when a mission is due (no scheduler in v1).

## 9. Assignments, availability & coverage

**Assignment FSM:** `proposed → accepted | declined` (crew decides; decline reason optional).
A holder of `ASSIGNMENT_MANAGE` may `remove` a proposed or accepted assignment at any time.
Declined/removed are terminal; re-proposing creates a new row. Proposing/removing is allowed while
the mission is in any non-terminal state.

**Availability (one rule, one selector — `selectors/staffing.py`):**

> A crew member is **hard-blocked** for a date range iff they hold an *accepted* assignment on an
> *approved or active* mission whose dates overlap it. Any other overlap (proposed anywhere;
> accepted on draft/pending/rejected missions) is a **soft conflict** — permitted, surfaced as a
> warning in matcher and staffing UI.

Consequence: two pending missions may both stage the same crew member; whichever is approved first
wins the reservation, and the second mission's approval fails its staffing validation with a clear
error naming the conflicted members. Only crew members (`role = CREW_MEMBER`, active) are assignable.

**Coverage semantics** (approve guard + staffing panel): a crew member may count toward requirements
of *different* skills simultaneously (generalists cover multiple requirements), but within one skill
fills only one requirement row. Validation per skill: sort requirement rows by `min_proficiency`
descending, sort qualified accepted crew by proficiency descending, match greedily — exact for this
nested structure, no search needed.

## 10. Matching engine

`missions/services/matching.py` — a pure function: mission in → proposal out, no side effects.
The lead reviews, swaps members, then bulk-creates `proposed` assignments.

1. **Expand** requirements into seats (`required_count = 2` → two seats). Subtract seats already
   covered by existing accepted assignments — the matcher fills gaps, it does not fight existing decisions.
2. **Pool** — active crew members in the tenant, minus hard-blocked, minus those already live-assigned
   to this mission.
3. **Score** each candidate per qualifying seat:
   `score = w₁·proficiency_fit + w₂·workload_balance − w₃·soft_conflict_penalty`
   — proficiency_fit rewards margin above `min_proficiency`; workload_balance rewards fewer accepted
   assignment-days (approved/active missions, ±90-day window); the penalty applies to overlapping
   soft conflicts. Weights are documented module constants, tunable at implementation.
4. **Select** greedily (weighted set-cover): repeatedly take the candidate covering the most open
   seats, ties broken by score; stop when seats are covered or `max_crew` reached. If covered but
   team < `min_crew`, top up with best-scoring remaining candidates.
5. **Explain** — every proposed member carries covered seats, score breakdown, and soft conflicts;
   every seat carries up to 3 ranked alternatives (powers the swap UI); unfilled seats carry a
   diagnosis: `no qualified crew` / `all qualified crew unavailable` / `max_crew too small`.

Deterministic: stable sorts, id tiebreaks — same inputs, same proposal.

## 11. API surface

`/api/v1`, JWT bearer, tenant-scoped, error envelope (§5), paginated lists (DRF limit/offset).

| Area | Endpoints |
|---|---|
| Auth | `POST /auth/token/` · `POST /auth/token/refresh/` · `GET /auth/me/` |
| Settings | `GET·PATCH /settings/organisation/` · `GET·POST /settings/users/` · `PATCH /settings/users/{id}/` |
| Skills | `GET /skills/` · `POST /skills/` · `PATCH /skills/{id}/` (archive = `is_archived`) |
| My profile | `GET·PUT /me/skills/` (bulk upsert own proficiencies) |
| Crew | `GET /crew/` · `GET /crew/{id}/` (skills + current load) |
| Missions | `GET·POST /missions/` (filters: status, date range, search) · `GET·PATCH /missions/{id}/` · `PUT /missions/{id}/requirements/` (bulk replace; draft/rejected only) · `POST /missions/{id}/transitions/` `{action, reason?}` · `GET /missions/{id}/staffing/` (per-requirement coverage + conflicts) |
| Matching | `POST /missions/{id}/match/` (pure; no side effects) |
| Assignments | `POST /missions/{id}/assignments/` (bulk propose `[{user_id}]`) · `POST /assignments/{id}/remove/` · `GET /me/assignments/` (nested mission summaries) · `POST /assignments/{id}/respond/` `{action: accept\|decline, reason?}` |
| Dashboard | `GET /dashboard/` (one payload, four widget groups) |

Every endpoint declares its required permission; transition permissions come from the FSM table (§8).

## 12. Frontend

### Routes

| Route | Permission | Content |
|---|---|---|
| `/login` | — | Email/password |
| `/` | `DASHBOARD_VIEW` | Dashboard; crew members redirect to `/my-assignments` |
| `/missions`, `/missions/:id` | `MISSION_VIEW` | List with status filter tabs; detail: status header + transition buttons (confirm dialog; reason field where required), requirements table (inline-edit in draft/rejected), staffing panel (coverage bars, soft-conflict chips), matcher dialog, history timeline |
| `/crew`, `/crew/:id` | `CREW_VIEW` | Directory; profile with skills and load |
| `/my-assignments` | `ASSIGNMENT_RESPOND` | Pending proposals (inline accept/decline), upcoming, history |
| `/my-profile` | `OWN_SKILLS_EDIT` | Own skills, inline editing |
| `/settings` | `SETTINGS_VIEW` | Tabs: Users (`USER_MANAGE`), Skills (`SKILL_MANAGE`), Organisation (`SETTINGS_MANAGE`) |

### Interaction patterns

Utilitarian minimalism: every element earns its place; low-probability info sits behind icons/popovers.
Big creates (mission) → dialog. Small edits (requirement rows, proficiencies, responses) → inline,
read view transforms into edit form. Designed empty/loading/error states on every list. Matcher dialog:
proposed team with score explanations, per-seat swap from ranked alternatives, one-click bulk propose.

## 13. Dashboard metrics

One `GET /dashboard/` payload; each group is an independent selector in `selectors/dashboard.py`:

1. **Mission pipeline** — counts by lifecycle state; pending-approval queue with age (from
   `MissionTransition`); missions starting in the next 30 days.
2. **Staffing readiness** — for missions in `pending_approval`, `approved`, or `active` whose
   `end_date` is today or later: % of requirements covered by accepted assignments; missions below
   `min_crew`; at-risk list (uncovered requirements or under-crewed).
3. **Crew utilization** — accepted assignment-days on approved/active missions in a rolling 90-day
   window as % of window, per crew member; org average; most/least loaded.
4. **Skill supply vs demand** — per skill: open seats across non-terminal missions vs distinct
   qualified crew (proficiency ≥ the rows' minimums); flagged gap when seats exceed qualified crew.

## 14. Testing strategy

- **Backend (pytest + factory_boy)**
  - Tenancy leak suite: every endpoint × another tenant's resources → 404; scoped manager without
    context → raises; composite-FK violations rejected at DB level.
  - FSM matrix: state × action × role, including self-approval block and guard failures.
  - Approve concurrency: two competing approvals over shared crew — exactly one succeeds.
  - Matcher unit suite: feasible/infeasible cases, generalist-beats-specialist, workload tiebreak,
    already-accepted subtraction, determinism.
  - RBAC matrix: parametrized role × endpoint → expected 200/403/404.
- **Frontend (vitest + RTL + MSW)** — route guards and permission-gated controls; matcher dialog flow;
  respond flow; zod schemas parsed against real API fixtures.

## 15. Seed data & delivery

- `manage.py seed_demo` — two contrasting tenants; users per role with documented credentials;
  ~15 crew each with varied skill profiles; missions across all seven states; deliberate
  soft-conflict cases so the matcher demo surfaces warnings; populated dashboard.
- README: `docker compose up` → migrate + seed → credential table → tour of the demo.
- CI (GitHub Actions): ruff + pytest; tsc + eslint + vitest + production build.

## 16. Implementation stages

Each stage lands with its tests green and is independently demoable.

1. **Foundations** — monorepo scaffold, Docker (dev + prod), CI; `common` (BaseModel, exception
   handler, pagination); `tenants` (model, context, scoped managers, DB hardening pattern); custom
   `User` + roles + permission catalog + authz service; JWT auth + `/auth/me/`; frontend shell
   (login, providers, router, route guards, layout); seed skeleton.
2. **Skills & people** — Skill CRUD (settings tabs: Users, Skills, Organisation); `CrewSkill` +
   `/me/skills/`; crew directory + profiles.
3. **Missions** — model + requirements + FSM + transition log; mission list/detail/create/edit UI,
   requirements editor, transition actions, history timeline.
4. **Assignments & availability** — Assignment model + FSM; staffing selector (availability,
   conflicts, coverage); propose/remove/respond APIs; staffing panel; my-assignments; approve guard
   wired to staffing validation.
5. **Matching** — engine + unit suite; match API; matcher dialog (team, explanations, swaps, bulk propose).
6. **Dashboard & polish** — four dashboard selectors + UI; full `seed_demo`; empty states; README.

## 17. Out of scope (v1)

Crew-defined availability/leave calendars; users spanning multiple tenants; notifications
(email/in-app); mission templates; scheduler-driven auto-activation/completion; requirement seat
pinning (assignments bind person ↔ mission, not person ↔ seat); soft-delete/undo; audit log beyond
mission transitions; `changes_requested`/`on_hold`/`archived` lifecycle states.
