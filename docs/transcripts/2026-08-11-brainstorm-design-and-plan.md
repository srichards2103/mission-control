# Transcript: 2026-08-11-brainstorm-design-and-plan

## 🧑 User — 2026-08-11 11:15

`/model`

## 🧑 User — 2026-08-11 11:15

`/model`

## 🧑 User — 2026-08-11 11:17

`/plugin`

## 🧑 User — 2026-08-11 11:17

`/superpowers:brainstorming`

<details><summary>📚 skill instructions loaded (collapsed)</summary>

```
Base directory for this skill: /Users/samrichards/.claude/plugins/cache/claude-plugins-official/superpowers/6.2.0/skills/brainstorming

# Brainstorming Ideas Into Designs

Help turn ideas into fully formed designs and specs through natural collaborat
… [9,647 more chars — see the .jsonl]
```

</details>

## 🧑 User — 2026-08-11 11:19

`/superpowers:brainstorming`

<details><summary>📚 skill instructions loaded (collapsed)</summary>

```
Base directory for this skill: /Users/samrichards/.claude/plugins/cache/claude-plugins-official/superpowers/6.2.0/skills/brainstorming

# Brainstorming Ideas Into Designs

Help turn ideas into fully formed designs and specs through natural collaborat
… [10,212 more chars — see the .jsonl]
```

</details>

### 🤖 Assistant — 2026-08-11 11:20

I've read both briefs. Let me set up the process tasks and check the repo state first.

- 🔧 **ToolSearch** · `query=select:TaskCreate,TaskUpdate,TaskList`

- 🔧 **Bash** · `command=ls -la /Users/samrichards/code/mission-control-mutinex && git -C /Users/samrichards/code/mission-control-mutinex log --oneline -20 2>&1 | head -25`

<details><summary>⤷ Bash result</summary>

```
total 24
drwxr-xr-x@  5 samrichards  staff   160 11 Aug 21:12 .
drwxr-xr-x  11 samrichards  staff   352 11 Aug 19:46 ..
drwxr-xr-x@  9 samrichards  staff   288 11 Aug 19:46 .git
-rw-r--r--@  1 samrichards  staff  8156 11 Aug 21:12 initial-brief.md
-rw-r--r--@  1 samrichards  staff  3358 11 Aug 20:08 project-brief.md
fatal: your current branch 'master' does not have any commits yet
```

</details>

### 🤖 Assistant — 2026-08-11 11:20

Fresh repo — no commits yet, just the two briefs. Setting up the process checklist, then I'll start with clarifying questions.

- 🔧 **TaskCreate** · `{"subject": "Explore project context", "description": "Read project-brief.md and initial-brief.md, check repo state and commits"}`

<details><summary>⤷ TaskCreate result</summary>

```
Task #1 created successfully: Explore project context
```

</details>

- 🔧 **TaskCreate** · `{"subject": "Ask clarifying questions", "description": "One at a time: resolve open design questions (assignment accept/reject, availability semantics, lifecycle states, matching approach, permissions, dashboard metrics,
… [53 more chars — see the .jsonl]`

<details><summary>⤷ TaskCreate result</summary>

```
Task #2 created successfully: Ask clarifying questions
```

</details>

- 🔧 **TaskCreate** · `{"subject": "Propose 2-3 approaches with trade-offs", "description": "Present design approach options for the key contested areas with a recommendation", "activeForm": "Proposing approaches"}`

<details><summary>⤷ TaskCreate result</summary>

```
Task #3 created successfully: Propose 2-3 approaches with trade-offs
```

</details>

- 🔧 **TaskCreate** · `{"subject": "Present design in sections for approval", "description": "Architecture, data model, matching engine, RBAC, API surface, frontend structure, testing — section by section with user sign-off", "activeForm": "Pr
… [26 more chars — see the .jsonl]`

<details><summary>⤷ TaskCreate result</summary>

```
Task #4 created successfully: Present design in sections for approval
```

</details>

- 🔧 **TaskCreate** · `{"subject": "Write design doc and commit", "description": "Save to docs/superpowers/specs/2026-08-11-mission-control-design.md and commit", "activeForm": "Writing design doc"}`

<details><summary>⤷ TaskCreate result</summary>

```
Task #5 created successfully: Write design doc and commit
```

</details>

- 🔧 **TaskCreate** · `{"subject": "Spec self-review", "description": "Scan for placeholders, contradictions, ambiguity, scope issues; fix inline", "activeForm": "Self-reviewing spec"}`

<details><summary>⤷ TaskCreate result</summary>

```
Task #6 created successfully: Spec self-review
```

</details>

- 🔧 **TaskCreate** · `{"subject": "User reviews written spec", "description": "Ask user to review the spec file before proceeding to planning"}`

<details><summary>⤷ TaskCreate result</summary>

```
Task #7 created successfully: User reviews written spec
```

</details>

- 🔧 **TaskCreate** · `{"subject": "Transition to writing-plans skill", "description": "Invoke writing-plans to create the staged end-to-end implementation plan"}`

<details><summary>⤷ TaskCreate result</summary>

```
Task #8 created successfully: Transition to writing-plans skill
```

</details>

- 🔧 **TaskUpdate** · `{"taskId": "1", "status": "completed"}`

- 🔧 **TaskUpdate** · `{"taskId": "2", "status": "in_progress"}`

<details><summary>⤷ TaskUpdate result</summary>

```
Updated task #1 status
```

</details>

<details><summary>⤷ TaskUpdate result</summary>

```
Updated task #2 status
```

</details>

- 🔧 **AskUserQuestion** · `{"questions": [{"question": "Should crew members accept/decline their assignments, or do leads assign directly with no crew response?", "header": "Assignments", "multiSelect": false, "options": [{"label": "Crew accept/de
… [975 more chars — see the .jsonl]`

<details><summary>⤷ AskUserQuestion result</summary>

```
Your questions have been answered: "Should crew members accept/decline their assignments, or do leads assign directly with no crew response?"="Crew accept/decline (Recommended)". You can now continue with these answers in mind.
```

</details>

- 🔧 **AskUserQuestion** · `{"questions": [{"question": "When does an existing assignment make a crew member unavailable for another mission's overlapping date range?", "header": "Availability", "multiSelect": false, "options": [{"label": "Approved
… [1,174 more chars — see the .jsonl]`

<details><summary>⤷ AskUserQuestion result</summary>

```
Your questions have been answered: "When does an existing assignment make a crew member unavailable for another mission's overlapping date range?"="Approved+active block (Recommended)". You can now continue with these answers in mind.
```

</details>

- 🔧 **AskUserQuestion** · `{"questions": [{"question": "What should the auto-matching engine produce, and how sophisticated should the algorithm be?", "header": "Matcher", "multiSelect": false, "options": [{"label": "Team builder + rationale (Reco
… [1,198 more chars — see the .jsonl]`

<details><summary>⤷ AskUserQuestion result</summary>

```
Your questions have been answered: "What should the auto-matching engine produce, and how sophisticated should the algorithm be?"="Team builder + rationale (Recommended)". You can now continue with these answers in mind.
```

</details>

- 🔧 **AskUserQuestion** · `{"questions": [{"question": "How should authentication work?", "header": "Auth", "multiSelect": false, "options": [{"label": "Session cookies (Recommended)", "description": "Django's built-in session auth over HttpOnly c
… [943 more chars — see the .jsonl]`

<details><summary>⤷ AskUserQuestion result</summary>

```
Your questions have been answered: "How should authentication work?"="JWT (simplejwt)". You can now continue with these answers in mind.
```

</details>

- 🔧 **AskUserQuestion** · `{"questions": [{"question": "Which metric groups should the director dashboard include in v1?", "header": "Dashboard", "multiSelect": true, "options": [{"label": "Mission pipeline (Recommended)", "description": "Missions
… [950 more chars — see the .jsonl]`

<details><summary>⤷ AskUserQuestion result</summary>

```
Your questions have been answered: "Which metric groups should the director dashboard include in v1?"="Mission pipeline (Recommended), Staffing readiness (Recommended), Crew utilization (Recommended), Skill supply vs demand". You can now continue with these answers in mind.
```

</details>

- 🔧 **TaskUpdate** · `{"taskId": "2", "status": "completed"}`

<details><summary>⤷ TaskUpdate result</summary>

```
Updated task #2 status
```

</details>

- 🔧 **TaskUpdate** · `{"taskId": "3", "status": "in_progress"}`

<details><summary>⤷ TaskUpdate result</summary>

```
Updated task #3 status
```

</details>

- 🔧 **AskUserQuestion** · `{"questions": [{"question": "Which mission lifecycle FSM shape should we build?", "header": "Lifecycle", "multiSelect": false, "options": [{"label": "Seven-state core (Recommended)", "description": "draft → pending_appro
… [2,148 more chars — see the .jsonl]`

<details><summary>⤷ AskUserQuestion result</summary>

```
Your questions have been answered: "Which mission lifecycle FSM shape should we build?"="Seven-state core (Recommended)" selected preview:
draft ─submit─▶ pending_approval ─approve─▶ approved ─activate─▶ active ─complete─▶ completed
  ▲                    │
  └──revise── rejected ◀─reject─┘

cancelled ◀─cancel─ (any state before completed)

• approve: director only, never own mission; re-validates crew conflicts + min crew
• activate: allowed once start date reached; final conflict check
• edit
… [91 more chars — see the .jsonl]
```

</details>

- 🔧 **TaskUpdate** · `{"taskId": "3", "status": "completed"}`

- 🔧 **TaskUpdate** · `{"taskId": "4", "status": "in_progress"}`

<details><summary>⤷ TaskUpdate result</summary>

```
Updated task #4 status
```

</details>

<details><summary>⤷ TaskUpdate result</summary>

```
Updated task #3 status
```

</details>

### 🤖 Assistant — 2026-08-11 11:34

All decisions are locked. I'll now present the design in four sections, pausing for your sign-off after each: **(1) architecture & tenancy foundations, (2) data model & RBAC, (3) lifecycles & matching engine, (4) API surface, frontend & testing**.

---

## Section 1 — Architecture & Foundations

### Repo layout

Monorepo, two top-level directories plus infrastructure:

```
backend/
  config/                 # settings (django-environ), urls, wsgi
  mission_control/
    common/               # BaseModel, pagination, exception handler, utils
    tenants/              # Tenant model, tenant context, TenantModel base + managers
    users/                # custom User, Role enum, permission catalog, authz service
    skills/               # Skill, CrewSkill
    missions/             # Mission, MissionRequirement, FSM + transition log
    assignments/          # Assignment + its small FSM
    matching/             # services only, no models — the engine
    dashboard/            # aggregate query services, no models
frontend/
  src/
    app/                  # router, providers, route composition
    components/ui/        # shadcn primitives
    features/             # auth, missions, crew, skills, assignments, matching, dashboard
    lib/                  # api client (axios + interceptors), authz hook, utils
docker-compose.dev.yml    # postgres + runserver + vite (proxy /api)
docker-compose.yml        # postgres + gunicorn + nginx (built SPA, /api proxy)
```

Each Django app follows Hacksoft conventions: `models.py`, `services.py` (all writes), `selectors.py` (all reads), `apis.py` (DRF `APIView`s with inline serializers, one service/selector call each). Each frontend feature follows bulletproof-react: `api/` (react-query hooks + zod schemas that parse every response), `components/`, `types/`.

### Multi-tenancy guardrails (the load-bearing part)

Four layers, fail-closed:

1. **Tenant context** — a `contextvars.ContextVar` holding the current tenant id. Because JWT auth happens in the DRF layer (not Django middleware), the context is set by a **custom simplejwt authentication class** immediately after the token resolves to a user, and a middleware guarantees reset after every request (and on exceptions).
2. **Scoped managers** — abstract `TenantModel(BaseModel)` with `tenant = FK(Tenant, PROTECT)`. Its default manager filters every queryset by the context tenant and auto-stamps `tenant` on create. If no tenant is in context, it **raises** rather than returning unscoped data. An explicit `objects_unscoped` manager exists for migrations/admin/tests only.
3. **Service-layer validation** — services validate that related objects (mission ↔ skill, assignment ↔ user) share a tenant before writing.
4. **Database hardening** — `UNIQUE(tenant_id, id)` on parent tables plus composite FKs `(tenant_id, <parent>_id)` on the high-risk join tables (`CrewSkill`, `MissionRequirement`, `Assignment`) via `RunSQL` migrations. Even buggy code physically cannot create a cross-tenant link.

### Auth & error handling

- **JWT via simplejwt** (your pick): short-lived access + rotating refresh with blacklist. Frontend keeps the access token in memory and the refresh token in `localStorage`; an axios interceptor transparently refreshes on 401 and retries once. `GET /auth/me` returns the user plus their computed permission list — the frontend's single source of authz truth.
- **Errors** — Hacksoft-style global exception handler. Services raise `ApplicationError(message, extra)`; the handler maps it and DRF's `ValidationError` / `PermissionDenied` / `NotFound` into one envelope: `{ "message": str, "extra": {...} }`. The frontend error path is written once against that shape.

Does this section look right, or would you adjust anything before I move to the data model & RBAC?

## 🧑 User — 2026-08-11 11:39

Do we really need to break it up that much in the backend. I would think we only need common, tenants, users, missions, and everything else is really just folded into the missions app. Unless you have a valid reason for exntending it to be so fat?

### 🤖 Assistant — 2026-08-11 11:39

You're right — there's no strong reason for that many apps. Django apps are domain boundaries, not file organisation; splitting `matching` and `dashboard` into apps when they own zero models is app-sprawl, and Hacksoft's own guidance is to build apps around domains, not features. The leaner cut works with one nuance:

- **`skills` belongs in `users`, not `missions`.** `Skill` and `CrewSkill` describe crew capability — they exist independently of any mission (crew edit their profiles, directors curate the taxonomy). Folding them into `missions` would make `users`-domain screens import from `missions`. Putting them in `users` keeps the dependency graph strictly one-way: `missions → users → tenants → common`.
- **Everything else folds into `missions`** as you suggest: `Mission`, `MissionRequirement`, `Assignment`, the FSM, the matcher, and the dashboard selectors (dashboard is just read-model queries over the missions domain — no models, so no app).

Revised layout — four apps, with packages instead of apps for internal organisation so files stay focused:

```
mission_control/
  common/       # BaseModel, pagination, exception handler
  tenants/      # Tenant, context, TenantModel base + scoped managers
  users/        # User, Role enum, permission catalog, Skill, CrewSkill
  missions/
    models.py             # Mission, MissionRequirement, Assignment
    services/             # missions.py, assignments.py, matching.py
    selectors/            # missions.py, staffing.py, dashboard.py
    apis/                 # one module per API group, inline serializers
```

Everything else in Section 1 (tenancy guardrails, JWT, error envelope) unchanged. Shall I move on to Section 2 — data model & RBAC?

## 🧑 User — 2026-08-11 11:40

yes

- 🔧 **TaskUpdate** · `{"taskId": "4", "activeForm": "Presenting design sections", "status": "in_progress"}`

<details><summary>⤷ TaskUpdate result</summary>

```
Updated task #4
```

</details>

### 🤖 Assistant — 2026-08-11 11:41

## Section 2 — Data Model & RBAC

### Data model

All tenant-scoped models inherit `TenantModel` (tenant FK + timestamps + scoped manager). Integer PKs; day-granularity dates (the brief's availability unit is "day x").

**`Tenant`** — `name`, `slug`.

**`User`** — custom user, global-unique `email` login, `tenant` FK, `role` (TextChoices: `DIRECTOR | MISSION_LEAD | CREW_MEMBER`), `name`, `is_active`. One nuance: `User` is the only tenant-scoped model that *can't* use the fail-closed scoped manager as its default — authentication has to resolve email → user *before* tenant context exists. It keeps a standard manager, and user-listing selectors scope by tenant explicitly.

**`Skill`** — `name`, `description`, `is_archived`. Unique on `(tenant, lower(name))`. Archived skills stay valid on existing records but can't be added to new profiles/requirements.

**`CrewSkill`** — `user` FK, `skill` FK, `proficiency` (DB check `1..10`), unique `(user, skill)`.

**`Mission`** — `name`, `description`, `start_date`, `end_date`, `status`, `min_crew`, `max_crew`, `created_by`. DB checks: `end_date >= start_date`, `1 <= min_crew <= max_crew`. Requirements/dates/crew-bounds editable only in `draft`/`rejected` (service-enforced).

**`MissionTransition`** — append-only log: `mission`, `from_status`, `to_status`, `actor`, `reason`, timestamp. This is the audit trail; rejection reasons and approval-queue aging come from here instead of stamp fields on `Mission`.

**`MissionRequirement`** — `mission` FK, `skill` FK, `min_proficiency` (`1..10`), `required_count` (`>=1`), unique `(mission, skill, min_proficiency)`. So "one pilot ≥9 **and** two pilots ≥5" is two rows — expressive without a seat table.

**`Assignment`** — `mission` FK, `user` FK, `status` (`proposed | accepted | declined | removed`), `decline_reason`, `created_by`, `responded_at`. **Partial unique index** on `(mission, user)` where status in (`proposed`, `accepted`) — one live assignment per person per mission, while declined/removed rows persist as history and re-proposing stays possible.

Plus the composite-FK tenant hardening from Section 1 on `CrewSkill`, `MissionRequirement`, `Assignment`.

### RBAC — the minimum permission set

Fourteen permissions. The trick that keeps it minimal: `submit/activate/complete/cancel` are all "advance a mission you run" and always travel together, so they collapse into one `MISSION_PROGRESS`; if a future role needs them split, we split the enum then.

| Group | Permissions |
|---|---|
| Missions | `MISSION_VIEW`, `MISSION_CREATE`, `MISSION_EDIT`, `MISSION_PROGRESS`, `MISSION_REVIEW` (approve/reject) |
| Assignments | `ASSIGNMENT_MANAGE` (propose/remove), `ASSIGNMENT_RESPOND` (accept/decline own) |
| Matching | `MATCH_RUN` |
| People | `CREW_VIEW`, `USER_MANAGE` |
| Skills | `SKILL_VIEW`, `SKILL_MANAGE`, `OWN_SKILLS_EDIT` |
| Dashboard | `DASHBOARD_VIEW` |

Role → permission sets (pure data, per your extensibility goal):

- **Director**: everything except `ASSIGNMENT_RESPOND` and `OWN_SKILLS_EDIT` (directors aren't assignable crew).
- **Mission Lead**: `MISSION_VIEW/CREATE/EDIT/PROGRESS`, `ASSIGNMENT_MANAGE`, `MATCH_RUN`, `CREW_VIEW`, `SKILL_VIEW`, `DASHBOARD_VIEW`.
- **Crew Member**: `SKILL_VIEW`, `OWN_SKILLS_EDIT`, `ASSIGNMENT_RESPOND`. Mission visibility comes only through their own assignments — no org-wide mission list, matching the brief's "limited visibility".

Three rules are **object-level invariants in services**, not permissions: (1) a reviewer can never approve/reject a mission they created or submitted — holds even for directors; (2) leads can only edit/progress missions they created, directors any; (3) `ASSIGNMENT_RESPOND` applies only to your own assignments. Page gating on the frontend maps one-to-one onto these permissions via `/auth/me`'s permission list, a `useAuthz` hook, and a `<RequirePermission>` route guard.

Look right? Next up is Section 3 — lifecycles, availability, and the matching engine internals.

## 🧑 User — 2026-08-11 11:44

Yep looks good, only thing is permisisons for settings, directors should probably also be able to create users, and all of the configuration would be gated behind a general settings page that we want to be permission backed as well

### 🤖 Assistant — 2026-08-11 11:44

Good call. Updated: a **Settings area** (tabs: Users, Skills, Organisation) becomes the home for all org configuration, gated by two new permissions — `SETTINGS_VIEW` (page access) and `SETTINGS_MANAGE` (org-level edits like renaming the organisation). Inside it, the Users tab is backed by `USER_MANAGE` (create users with a role, change roles, deactivate) and the Skills tab by `SKILL_MANAGE`. Both new permissions go to **directors only**; the catalog is now 16. `SKILL_VIEW` stays broadly granted since profile editors and requirement pickers need the taxonomy read-only.

---

## Section 3 — Lifecycles, Availability & the Matching Engine

### Mission FSM

The seven-state machine you approved, implemented as a transition table in `missions/services/missions.py` — one `transition_mission(actor, mission, action, reason=None)` service that checks: permission → object-level rules → state validity → domain guards, then writes the new status and a `MissionTransition` row atomically.

Guards per transition:

- **submit** (`draft → pending_approval`): at least one requirement exists.
- **approve** (`pending_approval → approved`): actor has `MISSION_REVIEW`, is not creator/submitter; **staffing re-validation** — every requirement covered by *accepted* assignments, accepted count within `[min_crew, max_crew]`, and no accepted crew member is hard-blocked by an overlapping approved/active mission. Runs inside a transaction with row locks on the affected assignments (two directors approving competing missions concurrently can't both win).
- **reject** (`pending_approval → rejected`): reason required.
- **revise** (`rejected → draft`): reopens editing.
- **activate** (`approved → active`): allowed once `start_date` ≤ today; re-runs the conflict check as a belt-and-braces guard.
- **complete** (`active → completed`): allowed once `end_date` ≤ today.
- **cancel** (any non-terminal state): reason required; live assignments flip to `removed`.

### Assignment FSM & availability

`proposed → accepted | declined` (crew decides, decline takes an optional reason); a lead/director can `remove` a proposed *or* accepted assignment at any time. Declined/removed are terminal — re-proposing creates a fresh row (history intact, allowed by the partial unique index).

Availability is one rule, computed in one selector (`staffing.py`) used by matcher, assignment creation, and approval alike:

> A crew member is **hard-blocked** for a date range iff they hold an *accepted* assignment on an *approved or active* mission whose dates overlap it. Anything else overlapping (proposed anywhere, accepted on draft/pending/rejected missions) is a **soft conflict** — allowed, but surfaced as a warning chip in the matcher and staffing UI.

Coverage semantics (used by the approve guard and the staffing panel): a crew member may count toward requirements of *different* skills simultaneously (the generalist case from your brief), but within one skill they fill only one requirement row. Per skill: sort requirement rows by `min_proficiency` descending, sort qualified accepted crew by proficiency descending, match greedily — for this nested structure greedy is provably exact, so validation is simple *and* correct.

### Matching engine (`missions/services/matching.py`)

Pure function, no side effects: mission in → proposal out. The lead reviews, optionally swaps members, then bulk-creates `proposed` assignments in one call.

1. **Expand** requirements into seats (a `required_count=2` row is two seats). Subtract seats already covered by existing accepted assignments — the matcher fills *gaps*, it doesn't fight decisions already made.
2. **Pool** — active crew in the tenant, minus hard-blocked members, minus those already live-assigned to this mission.
3. **Score** each candidate per seat they qualify for:
 `score = w₁·proficiency_fit + w₂·workload_balance − w₃·soft_conflict_penalty`
 where proficiency_fit rewards margin above `min_proficiency`, workload_balance rewards fewer accepted assignment-days in a ±90-day window (spreads load across the org), and the penalty applies when the candidate has overlapping soft conflicts. Weights are module constants — tunable, documented.
4. **Select** greedily (weighted set-cover): repeatedly take the candidate whose seat-coverage is largest, breaking ties by score; a versatile generalist covering three seats beats a specialist covering one. Stop when seats are covered or `max_crew` is reached. If covered but team < `min_crew`, top up with best-scoring remaining candidates.
5. **Explain** — output is a proposed team where every member carries: seats they cover, score breakdown, and any soft conflicts; each seat carries up to 3 ranked alternatives (powers swap UI); unfilled seats carry a diagnosis (`no qualified crew` / `all qualified crew are unavailable` / `max_crew too small to cover requirements`). Fully deterministic (stable sort, id tiebreak) — same inputs, same proposal, testable.

Look right? Last section after this: API surface, frontend screens, testing & seed data.

## 🧑 User — 2026-08-11 11:48

yep, one thing to note on each transition is that we must check that the user tryign to transition has the required permission for that transition. Otherwise looks right, we can tweak the matching algorithm when it's implemented

### 🤖 Assistant — 2026-08-11 11:49

Noted — and agreed: the transition table itself carries the required permission per action, so the check is data, not scattered ifs: `submit/revise/activate/complete/cancel → MISSION_PROGRESS` (owner lead or any director), `approve/reject → MISSION_REVIEW` (+ never your own mission). A transition without its permission raises `PermissionDenied` before any guard runs. Matcher weights stay tunable constants we'll calibrate during implementation.

---

## Section 4 — API Surface, Frontend & Testing

### API surface (`/api/v1`, JWT bearer, error envelope, paginated lists)

| Area | Endpoints |
|---|---|
| Auth | `POST /auth/token/`, `POST /auth/token/refresh/`, `GET /auth/me/` (user + permissions) |
| Settings | `GET·PATCH /settings/organisation/` · `GET·POST /settings/users/`, `PATCH /settings/users/{id}/` (role, deactivate) |
| Skills | `GET /skills/` · `POST·PATCH /skills/{id}/` (archive = PATCH `is_archived`) |
| My profile | `GET·PUT /me/skills/` (bulk upsert own proficiencies) |
| Crew | `GET /crew/`, `GET /crew/{id}/` (skills + current load) |
| Missions | `GET·POST /missions/`, `GET·PATCH /missions/{id}/`, `PUT /missions/{id}/requirements/` (bulk replace, draft/rejected only), `POST /missions/{id}/transitions/` `{action, reason?}` — one endpoint mirroring the FSM table, `GET /missions/{id}/staffing/` (per-requirement coverage + conflicts) |
| Matching | `POST /missions/{id}/match/` — pure, no side effects |
| Assignments | `POST /missions/{id}/assignments/` (bulk propose), `POST /assignments/{id}/remove/`, `GET /me/assignments/`, `POST /assignments/{id}/respond/` `{action: accept\|decline, reason?}` |
| Dashboard | `GET /dashboard/` — one payload, four widget groups |

### Frontend routes & interaction patterns

- `/login` · `/` = dashboard (crew members redirect to `/my-assignments`)
- `/missions` — list with status filter tabs → `/missions/:id` — status header with transition buttons (confirm dialog, reason field where required), requirements table (inline-editable in draft/rejected), staffing panel (coverage bars per requirement, soft-conflict warning chips), matcher dialog (proposed team, score explanations, per-seat swap from alternatives, bulk-propose button), history timeline from `MissionTransition`.
- `/crew` → `/crew/:id` — profile with skills and load.
- `/my-assignments` — crew home: pending proposals with inline accept/decline, upcoming, history. `/my-profile` — own skills, inline editing.
- `/settings` — Users / Skills / Organisation tabs (directors).

Patterns follow your ethos: big creates (mission) get a dialog; small edits (requirement rows, proficiencies, responses) happen inline; low-probability info sits behind icons/popovers. Every list has designed empty/loading/error states.

### Testing & delivery

- **Backend (pytest + factory_boy)** — tenancy leak suite (every endpoint against another tenant's resources → 404; scoped manager without context → raises); FSM transition matrix (state × action × role, incl. self-approval block); approve-guard concurrency test (two competing approvals, row locks); matcher unit suite (feasibility, generalist-beats-specialist, workload tiebreak, determinism); parametrized RBAC matrix (role × endpoint).
- **Frontend (vitest + RTL + MSW)** — route guards and permission-gated UI, matcher dialog flow, respond flow, zod schemas parsed against real API fixtures.
- **Seed & demo** — `manage.py seed_demo`: two contrasting tenants, users per role with documented credentials, ~15 crew each, missions across all seven states, deliberate soft-conflict cases so the matcher demo shows its warnings. README: `docker compose up` → seeded → credential table.
- **CI** — GitHub Actions: ruff + pytest; tsc + eslint + vitest + build.

That's the full design. Anything to adjust — or shall I write it up as the spec (`docs/superpowers/specs/2026-08-11-mission-control-design.md`), self-review it, and hand it to you for final review?

## 🧑 User — 2026-08-11 11:50

yep write it up

- 🔧 **TaskUpdate** · `{"taskId": "4", "status": "completed"}`

<details><summary>⤷ TaskUpdate result</summary>

```
Updated task #4 status
```

</details>

- 🔧 **TaskUpdate** · `{"taskId": "5", "status": "in_progress"}`

<details><summary>⤷ TaskUpdate result</summary>

```
Updated task #5 status
```

</details>

- 🔧 **Write** · `file_path=/Users/samrichards/code/mission-control-mutinex/docs/superpowers/specs/2026-08-11-mission-control-design.md (+edit)`

<details><summary>⤷ Write result</summary>

```
File created successfully at: /Users/samrichards/code/mission-control-mutinex/docs/superpowers/specs/2026-08-11-mission-control-design.md (file state is current in your context — no need to Read it back)
```

</details>

- 🔧 **TaskUpdate** · `{"taskId": "6", "status": "in_progress"}`

<details><summary>⤷ TaskUpdate result</summary>

```
Updated task #6 status
```

</details>

### 🤖 Assistant — 2026-08-11 11:53

One ambiguity found: §13's staffing readiness said "approved + upcoming missions", which could be read two ways. Making it precise:

- 🔧 **Edit** · `file_path=/Users/samrichards/code/mission-control-mutinex/docs/superpowers/specs/2026-08-11-mission-control-design.md (+edit)`

<details><summary>⤷ Edit result</summary>

```
The file /Users/samrichards/code/mission-control-mutinex/docs/superpowers/specs/2026-08-11-mission-control-design.md has been updated successfully. (file state is current in your context — no need to Read it back)
```

</details>

- 🔧 **Bash** · `command=git add docs/superpowers/specs/2026-08-11-mission-control-design.md && git commit -m "$(cat <<'EOF' ⏎ Add Mission Control design spec ⏎  ⏎ Approved design for the multi-tenant mission/crew platform: architecture,
… [262 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
[master (root-commit) ce1cd37] Add Mission Control design spec
 1 file changed, 310 insertions(+)
 create mode 100644 docs/superpowers/specs/2026-08-11-mission-control-design.md
ce1cd37 Add Mission Control design spec
```

</details>

- 🔧 **TaskUpdate** · `{"taskId": "5", "status": "completed"}`

<details><summary>⤷ TaskUpdate result</summary>

```
Updated task #5 status
```

</details>

- 🔧 **TaskUpdate** · `{"taskId": "6", "status": "completed"}`

<details><summary>⤷ TaskUpdate result</summary>

```
Updated task #6 status
```

</details>

- 🔧 **TaskUpdate** · `{"taskId": "7", "status": "in_progress"}`

<details><summary>⤷ TaskUpdate result</summary>

```
Updated task #7 status
```

</details>

### 🤖 Assistant — 2026-08-11 11:53

Spec written and committed to `docs/superpowers/specs/2026-08-11-mission-control-design.md` (initial commit `ce1cd37`).

The self-review pass found and fixed one ambiguity — the staffing-readiness metric now precisely scopes which missions it covers (`pending_approval`/`approved`/`active`, not yet ended) instead of the vague "approved + upcoming". Everything else checked out: the permission catalog counts to exactly 16, every FSM transition in the table carries its permission, the availability rule is stated once and referenced everywhere, and coverage semantics in §9 match the requirement uniqueness constraint in §6. Deliberate deferrals (matcher weight calibration) are marked as such rather than left as TBDs, and there's an explicit out-of-scope list so v1 boundaries are unambiguous.

Please review the spec and let me know if you want to make any changes before we start writing out the staged implementation plan.

## 🧑 User — 2026-08-11 11:55

Write out the staged implementation plan

- 🔧 **TaskUpdate** · `{"taskId": "7", "status": "completed"}`

- 🔧 **TaskUpdate** · `{"taskId": "8", "status": "in_progress"}`

<details><summary>⤷ TaskUpdate result</summary>

```
Updated task #8 status
```

</details>

<details><summary>⤷ TaskUpdate result</summary>

```
Updated task #7 status
```

</details>

- 🔧 **Skill** · `skill=superpowers:writing-plans`

<details><summary>⤷ Skill result</summary>

```
Launching skill: superpowers:writing-plans
```

</details>

<details><summary>📚 skill instructions loaded (collapsed)</summary>

```
Base directory for this skill: /Users/samrichards/.claude/plugins/cache/claude-plugins-official/superpowers/6.2.0/skills/writing-plans

# Writing Plans

## Overview

Write comprehensive implementation plans assuming the engineer has zero context for
… [6,954 more chars — see the .jsonl]
```

</details>

- 🔧 **Write** · `file_path=/Users/samrichards/code/mission-control-mutinex/docs/superpowers/plans/2026-08-11-mission-control/00-overview.md (+edit)`

<details><summary>⤷ Write result</summary>

```
File created successfully at: /Users/samrichards/code/mission-control-mutinex/docs/superpowers/plans/2026-08-11-mission-control/00-overview.md (file state is current in your context — no need to Read it back)
```

</details>

### 🤖 Assistant — 2026-08-11 12:00

Overview done. Now Stage 1 — Foundations, the pattern-setting plan.

- 🔧 **Write** · `file_path=/Users/samrichards/code/mission-control-mutinex/docs/superpowers/plans/2026-08-11-mission-control/01-foundations.md (+edit)`

<details><summary>⤷ Write result</summary>

```
File created successfully at: /Users/samrichards/code/mission-control-mutinex/docs/superpowers/plans/2026-08-11-mission-control/01-foundations.md (file state is current in your context — no need to Read it back)
```

</details>

### 🤖 Assistant — 2026-08-11 12:03

Stage 1 written. Now Stage 2 — Skills & people.

- 🔧 **Write** · `file_path=/Users/samrichards/code/mission-control-mutinex/docs/superpowers/plans/2026-08-11-mission-control/02-skills-people.md (+edit)`

<details><summary>⤷ Write result</summary>

```
File created successfully at: /Users/samrichards/code/mission-control-mutinex/docs/superpowers/plans/2026-08-11-mission-control/02-skills-people.md (file state is current in your context — no need to Read it back)
```

</details>

### 🤖 Assistant — 2026-08-11 12:06

Stage 3 — Missions, FSM, and lifecycle UI.

- 🔧 **Write** · `file_path=/Users/samrichards/code/mission-control-mutinex/docs/superpowers/plans/2026-08-11-mission-control/03-missions.md (+edit)`

<details><summary>⤷ Write result</summary>

```
File created successfully at: /Users/samrichards/code/mission-control-mutinex/docs/superpowers/plans/2026-08-11-mission-control/03-missions.md (file state is current in your context — no need to Read it back)
```

</details>

### 🤖 Assistant — 2026-08-11 12:10

Stage 4 — Assignments, availability, and the approve guard.

- 🔧 **Write** · `file_path=/Users/samrichards/code/mission-control-mutinex/docs/superpowers/plans/2026-08-11-mission-control/04-assignments.md (+edit)`

<details><summary>⤷ Write result</summary>

```
File created successfully at: /Users/samrichards/code/mission-control-mutinex/docs/superpowers/plans/2026-08-11-mission-control/04-assignments.md (file state is current in your context — no need to Read it back)
```

</details>

### 🤖 Assistant — 2026-08-11 12:13

Stage 5 — the matching engine.

- 🔧 **Write** · `file_path=/Users/samrichards/code/mission-control-mutinex/docs/superpowers/plans/2026-08-11-mission-control/05-matching.md (+edit)`

<details><summary>⤷ Write result</summary>

```
File created successfully at: /Users/samrichards/code/mission-control-mutinex/docs/superpowers/plans/2026-08-11-mission-control/05-matching.md (file state is current in your context — no need to Read it back)
```

</details>

### 🤖 Assistant — 2026-08-11 12:16

Stage 6 — Dashboard, seed, and polish.

- 🔧 **Write** · `file_path=/Users/samrichards/code/mission-control-mutinex/docs/superpowers/plans/2026-08-11-mission-control/06-dashboard-polish.md (+edit)`

<details><summary>⤷ Write result</summary>

```
File created successfully at: /Users/samrichards/code/mission-control-mutinex/docs/superpowers/plans/2026-08-11-mission-control/06-dashboard-polish.md (file state is current in your context — no need to Read it back)
```

</details>

- 🔧 **Edit** · `file_path=/Users/samrichards/code/mission-control-mutinex/docs/superpowers/plans/2026-08-11-mission-control/01-foundations.md (+edit)`

<details><summary>⤷ Edit result</summary>

```
The file /Users/samrichards/code/mission-control-mutinex/docs/superpowers/plans/2026-08-11-mission-control/01-foundations.md has been updated successfully. (file state is current in your context — no need to Read it back)
```

</details>

- 🔧 **Edit** · `file_path=/Users/samrichards/code/mission-control-mutinex/docs/superpowers/plans/2026-08-11-mission-control/02-skills-people.md (+edit)`

<details><summary>⤷ Edit result</summary>

```
The file /Users/samrichards/code/mission-control-mutinex/docs/superpowers/plans/2026-08-11-mission-control/02-skills-people.md has been updated successfully. (file state is current in your context — no need to Read it back)
```

</details>

- 🔧 **Edit** · `file_path=/Users/samrichards/code/mission-control-mutinex/docs/superpowers/plans/2026-08-11-mission-control/03-missions.md (+edit)`

<details><summary>⤷ Edit result</summary>

```
The file /Users/samrichards/code/mission-control-mutinex/docs/superpowers/plans/2026-08-11-mission-control/03-missions.md has been updated successfully. (file state is current in your context — no need to Read it back)
```

</details>

- 🔧 **Edit** · `file_path=/Users/samrichards/code/mission-control-mutinex/docs/superpowers/plans/2026-08-11-mission-control/03-missions.md (+edit)`

<details><summary>⤷ Edit result</summary>

```
The file /Users/samrichards/code/mission-control-mutinex/docs/superpowers/plans/2026-08-11-mission-control/03-missions.md has been updated successfully. (file state is current in your context — no need to Read it back)
```

</details>

- 🔧 **Edit** · `file_path=/Users/samrichards/code/mission-control-mutinex/docs/superpowers/plans/2026-08-11-mission-control/04-assignments.md (+edit)`

<details><summary>⤷ Edit result</summary>

```
The file /Users/samrichards/code/mission-control-mutinex/docs/superpowers/plans/2026-08-11-mission-control/04-assignments.md has been updated successfully. (file state is current in your context — no need to Read it back)
```

</details>

- 🔧 **Edit** · `file_path=/Users/samrichards/code/mission-control-mutinex/docs/superpowers/plans/2026-08-11-mission-control/04-assignments.md (+edit)`

<details><summary>⤷ Edit result</summary>

```
The file /Users/samrichards/code/mission-control-mutinex/docs/superpowers/plans/2026-08-11-mission-control/04-assignments.md has been updated successfully. (file state is current in your context — no need to Read it back)
```

</details>

- 🔧 **Edit** · `file_path=/Users/samrichards/code/mission-control-mutinex/docs/superpowers/plans/2026-08-11-mission-control/06-dashboard-polish.md (+edit)`

<details><summary>⤷ Edit result</summary>

```
The file /Users/samrichards/code/mission-control-mutinex/docs/superpowers/plans/2026-08-11-mission-control/06-dashboard-polish.md has been updated successfully. (file state is current in your context — no need to Read it back)
```

</details>

- 🔧 **Edit** · `file_path=/Users/samrichards/code/mission-control-mutinex/docs/superpowers/plans/2026-08-11-mission-control/06-dashboard-polish.md (+edit)`

<details><summary>⤷ Edit result</summary>

```
The file /Users/samrichards/code/mission-control-mutinex/docs/superpowers/plans/2026-08-11-mission-control/06-dashboard-polish.md has been updated successfully. (file state is current in your context — no need to Read it back)
```

</details>

- 🔧 **Bash** · `command=git add docs/superpowers/plans && git commit -m "$(cat <<'EOF' ⏎ Add staged implementation plan for Mission Control ⏎  ⏎ Six stage plans plus overview with global constraints and file map: ⏎ foundations (tenancy,
… [278 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
[master 6cf49ac] Add staged implementation plan for Mission Control
 7 files changed, 5071 insertions(+)
 create mode 100644 docs/superpowers/plans/2026-08-11-mission-control/00-overview.md
 create mode 100644 docs/superpowers/plans/2026-08-11-mission-control/01-foundations.md
 create mode 100644 docs/superpowers/plans/2026-08-11-mission-control/02-skills-people.md
 create mode 100644 docs/superpowers/plans/2026-08-11-mission-control/03-missions.md
 create mode 100644 docs/superpowers/plans/2026
… [317 more chars — see the .jsonl]
```

</details>

- 🔧 **TaskUpdate** · `{"taskId": "8", "status": "completed"}`

<details><summary>⤷ TaskUpdate result</summary>

```
Updated task #8 status
```

</details>

### 🤖 Assistant — 2026-08-11 12:19

Plan complete and saved to `docs/superpowers/plans/2026-08-11-mission-control/` (committed as `6cf49ac`, ~5,000 lines across 7 files).

**Structure:** `00-overview.md` carries the global constraints (error envelope, tenancy rules, permission values, API conventions) that every task inherits, plus the complete file map. Then one plan per stage, matching the spec's §16 breakdown — each stage lands with green tests and is independently demoable:

1. **Foundations** — scaffold, Docker, CI, tenant context + fail-closed managers, User/roles/16-permission catalog, JWT auth, error envelope, frontend shell with login and permission-gated nav (9 tasks)
2. **Skills & people** — first concrete tenant models with the composite-FK hardening pattern and the tenancy leak test suite, settings area, my-profile, crew directory (7 tasks)
3. **Missions** — models, the FSM as a transition table with per-action permissions, CRUD + lifecycle APIs, mission list/detail UI (5 tasks)
4. **Assignments** — availability/coverage selectors (the single source), propose/respond flows, the approve guard with crew-row locking, staffing panel, my-assignments (6 tasks)
5. **Matching** — the greedy set-cover engine with full unit suite (generalist-beats-specialists, workload tiebreaks, infeasibility diagnoses, determinism), match API, matcher dialog with swaps (3 tasks)
6. **Dashboard & polish** — four metric selectors, dashboard UI, rich idempotent seed, RBAC matrix test, README, prod delivery checks (3 tasks)

Every task specifies exact files, an Interfaces block (what it consumes/produces so tasks can be implemented independently), failing-test-first steps with real test code, and implementations for the load-bearing logic. The self-review caught and fixed five issues: tenant-context leakage between tests, a `full_clean` exclusion that would've turned duplicate-skill 400s into 500s, fixed calendar dates that would rot, two Stage-3 tests that break when Stage 4 wires the staffing guard (now updated in Task 4.4), and the missing parametrized RBAC matrix from spec §14.

**Two execution options:**

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration
2. **Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?

## 🧑 User — 2026-08-11 12:21

First things first, why aren't the plans showing up in git, i want to commit to the repo so i have a fresh state to work from

### 🤖 Assistant — 2026-08-11 12:21

Let me check the actual git state.

- 🔧 **Bash** · `command=git status && echo "---" && git log --oneline --stat`

<details><summary>⤷ Bash result</summary>

```
On branch master
Untracked files:
  (use "git add <file>..." to include in what will be committed)
	initial-brief.md
	project-brief.md

nothing added to commit but untracked files present (use "git add" to track)
---
6cf49ac Add staged implementation plan for Mission Control
 .../2026-08-11-mission-control/00-overview.md      |   76 +
 .../2026-08-11-mission-control/01-foundations.md   | 1494 ++++++++++++++++++++
 .../2026-08-11-mission-control/02-skills-people.md |  994 +++++++++++++
 .../2026-
… [455 more chars — see the .jsonl]
```

</details>

- 🔧 **Bash** · `command=git add initial-brief.md project-brief.md && git commit -m "$(cat <<'EOF' ⏎ Add project briefs ⏎  ⏎ Original challenge brief and initial direction notes that the design ⏎ spec and implementation plan were derived
… [112 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
[master c83bcca] Add project briefs
 2 files changed, 91 insertions(+)
 create mode 100644 initial-brief.md
 create mode 100644 project-brief.md
On branch master
nothing to commit, working tree clean
c83bcca Add project briefs
6cf49ac Add staged implementation plan for Mission Control
ce1cd37 Add Mission Control design spec
```

</details>

### 🤖 Assistant — 2026-08-11 12:21

Working tree is now clean. The repo history is:

- `ce1cd37` — design spec (`docs/superpowers/specs/`)
- `6cf49ac` — staged implementation plan (`docs/superpowers/plans/2026-08-11-mission-control/`)
- `c83bcca` — the two original briefs

You have a fresh state to work from. Ready to start execution whenever you are — just say whether you want **subagent-driven** (fresh subagent per task, I review between tasks — recommended) or **inline** execution.
