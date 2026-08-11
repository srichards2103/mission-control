# Mission Control Implementation Plan — Overview

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Mission Control — a multi-tenant B2B platform for mission planning, crew skill profiles, an auto-matching engine, and an org dashboard — per the approved spec at `docs/superpowers/specs/2026-08-11-mission-control-design.md`.

**Architecture:** Django + DRF backend (HackSoft style: services/selectors, APIViews with inline serializers) with single-database multi-tenancy enforced by a context-var + fail-closed scoped managers + composite-FK DB hardening. React SPA (Vite, shadcn/ui, TanStack Query, zod, bulletproof-react layout) talking JWT to `/api/v1`. Docker Compose for dev and prod.

**Tech Stack:** Python 3.12, Django ≥5.2, DRF ≥3.16, djangorestframework-simplejwt ≥5.5, psycopg 3, PostgreSQL 16, uv (package manager), pytest + factory_boy, ruff · Node 22, React 19, TypeScript 5, Vite 6, Tailwind CSS v4, shadcn/ui, TanStack Query v5, react-router v7, axios, zod, vitest + Testing Library + MSW.

## Plan files (execute in order)

| File | Stage | Delivers |
|---|---|---|
| `01-foundations.md` | 1 | Repo scaffold, Docker, CI, tenancy machinery, User+roles+permission catalog, JWT auth, error handler, frontend shell with login + route guards |
| `02-skills-people.md` | 2 | Skill/CrewSkill models + tenancy hardening pattern, skills & users settings, my-profile editor, crew directory |
| `03-missions.md` | 3 | Mission/Requirement/Transition models, FSM service, mission CRUD + lifecycle UI |
| `04-assignments.md` | 4 | Assignment model, availability/coverage selectors, propose/respond flows, approve guard wiring, staffing panel, my-assignments |
| `05-matching.md` | 5 | Matching engine + match API + matcher dialog with swaps and bulk propose |
| `06-dashboard-polish.md` | 6 | Dashboard selectors + UI, full seed_demo, README, prod verification |

## Global Constraints

Every task's requirements implicitly include these. Exact values from the spec:

- **Backend layout:** four Django apps only — `mission_control.common`, `mission_control.tenants`, `mission_control.users`, `mission_control.missions`. Dependency direction strictly `missions → users → tenants → common`. Matching + dashboard are modules inside `missions`, never apps.
- **HackSoft conventions:** all writes in `services`, all reads in `selectors`, APIs are DRF `APIView` subclasses with serializers defined **inline** in the API class, each API calls exactly one service/selector.
- **Error envelope:** every non-2xx response body is `{"message": str, "extra": dict}`. Validation errors: `message="Validation error"`, `extra={"fields": {...}}`.
- **Tenancy:** tenant-scoped models inherit `TenantModel`; default manager (`objects`) filters by the context tenant and **raises `TenantContextNotSet` when no tenant is in context**; `objects_unscoped` for migrations/tests only. Cross-tenant API access returns **404, never 403**. `UNIQUE(tenant_id, id)` on `User`, `Skill`, `Mission` + composite FKs on `CrewSkill`, `MissionRequirement`, `Assignment`.
- **Permissions:** the 16-permission catalog and role sets from spec §7, values e.g. `mission.view`, `mission.progress`, `settings.manage`. Backend raises DRF `PermissionDenied`; frontend gates via `/auth/me/` permission list. Object-level invariants: no self-approval (creator **or** submitter), leads edit/progress only own missions, respond only to own assignments.
- **Mission FSM:** seven states `draft, pending_approval, approved, rejected, active, completed, cancelled`; transitions + permissions exactly per spec §8, executed atomically with a `MissionTransition` audit row.
- **Availability rule (single source):** hard-block iff *accepted* assignment on *approved/active* mission with overlapping dates; everything else overlapping is a soft conflict. Date overlap test: `a.start_date <= b.end_date AND b.start_date <= a.end_date`. Day granularity (`DateField`).
- **API:** all under `/api/v1/`, JWT bearer, lists paginated with `{"results": [...], "count": n, "limit": n, "offset": n}`.
- **Frontend:** bulletproof-react feature folders (`src/features/<name>/{api,components}`), every API response parsed with zod, access token in memory + refresh token in `localStorage` key `mc_refresh`, axios interceptor refreshes once on 401 then logs out.
- **Testing:** backend pytest (+pytest-django, factory_boy) against PostgreSQL; frontend vitest + Testing Library + MSW. Commit only with green tests.
- **Commits:** conventional messages (`feat:`, `test:`, `chore:`), one commit per task minimum.

## Complete file map

```
backend/
  pyproject.toml, manage.py, .env.example, Dockerfile
  config/{__init__,settings,urls,wsgi}.py
  mission_control/__init__.py
  mission_control/common/{__init__,apps,models,exceptions,exception_handler,pagination}.py
  mission_control/tenants/{__init__,apps,models,context,middleware,services}.py + migrations/
  mission_control/users/{__init__,apps,models,roles,permissions,authentication,services,selectors,factories}.py
  mission_control/users/apis/{__init__,auth,skills,crew,profile,settings}.py + urls.py + migrations/
  mission_control/missions/{__init__,apps,models,factories,urls}.py + migrations/
  mission_control/missions/services/{__init__,missions,assignments,matching}.py
  mission_control/missions/selectors/{__init__,missions,staffing,dashboard}.py
  mission_control/missions/apis/{__init__,missions,assignments,matching,dashboard}.py
  tests/  (mirrors app layout: tests/tenants/, tests/users/, tests/missions/)
frontend/
  package.json, vite.config.ts, tsconfig.json, index.html, Dockerfile
  src/main.tsx
  src/app/{provider,router}.tsx
  src/components/layout/app-layout.tsx
  src/lib/{api-client.ts,auth.tsx,utils.ts}
  src/features/auth/{api/auth.ts,components/login-form.tsx}
  src/features/skills/{api/skills.ts,components/*}
  src/features/settings/{api/settings.ts,components/*}
  src/features/crew/{api/crew.ts,components/*}
  src/features/profile/{api/profile.ts,components/*}
  src/features/missions/{api/missions.ts,components/*}
  src/features/assignments/{api/assignments.ts,components/*}
  src/features/matching/{api/matching.ts,components/*}
  src/features/dashboard/{api/dashboard.ts,components/*}
docker-compose.dev.yml, docker-compose.yml, nginx.conf
.github/workflows/ci.yml
README.md
```

## Stage gate

A stage is done when: all its tasks' checkboxes are ticked, `uv run pytest` and `npm test`/`npm run build` are green, and the stage's demo path works in `docker compose -f docker-compose.dev.yml up`.
