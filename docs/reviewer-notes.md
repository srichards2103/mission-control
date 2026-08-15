# Reviewer notes

Notes on how this codebase was built, and a short list of known loose ends I chose
not to address in the available time.

## How this was built

I started from the two briefs in the repo root — `project-brief.md` and
`initial-brief.md` — and used Claude with the Superpowers **brainstorming** skill to
turn them into a comprehensive design document and a step-by-step implementation
plan. Both are checked in:

- Design: `docs/superpowers/specs/2026-08-11-mission-control-design.md`
- Plan: `docs/superpowers/plans/2026-08-11-mission-control/` (00-overview through
  06-dashboard-polish)

Once the plan existed, I let Claude agents execute it step by step, asynchronously,
while I was at work. Each plan task was implemented under a TDD process (test first,
then implementation, then review) enforced by the Superpowers skills.

**Why this shape.** Given the timeframe, it was never realistic for me to read every
line of generated code — and that risk is exactly what the process is designed to
contain. Enforcing a pre-agreed, reviewable plan and requiring TDD at every step
means each increment is small, specified in advance, and proven by tests written
before the code, which sharply reduces the chance of ending up with a pile of AI
slop at the end. The test suite, the plan documents, and the audit trail of
commits are the review surface, in place of line-by-line reading.

**Where I spent my own attention.** Backend modelling. For an app like this —
multi-tenancy, a mission lifecycle FSM, an availability/conflict predicate, and a
matching engine — the data model and domain rules are the expensive things to get
wrong; the frontend is comparatively cheap to change. That bet played out as
expected: the generated UI was serviceable but rough (centered prototype layout,
pill-heavy tables, lexicographic "Crew 10 before Crew 2" seed data), so the final
stretch was a deliberate UI pass — design tokens, shared primitives, then a sweep of
every page onto them — plus realistic seed data.

## Loose ends (known, not addressed)

### 1. Skill edits after assignment ("skill drift")

**The case:** a crew member is accepted onto a mission on the strength of their
skill profile, then edits that profile (downgrades or removes a skill), potentially
putting the mission's coverage at risk.

**What happens today:** nothing guards this. `crew_skills_set` replaces the profile
wholesale with no reference to existing assignments. Coverage is always recomputed
live from `CrewSkill`, so the drift *is* visible passively — the staffing panel and
dashboard skill-gap card will show the regression — but nobody is told, and nothing
blocks:

- A `pending_approval` mission will fail its approve guard later (approve re-runs
  full staffing validation), so drift is caught there.
- An **approved** mission is the gap: the activate guard deliberately re-checks
  *conflicts only*, not coverage (a documented decision — coverage regressions via
  crew removal/deactivation shouldn't block an already-approved mission), so a
  mission can activate under-covered after a skill edit with no flag raised.

**Best approach, if it were in scope:** don't block the edit — a profile edit is a
correction of fact about a person, and refusing it just preserves fiction in the
database. Instead:

1. **Warn on save**: when the edit would drop coverage on any approved/active
   mission the member is accepted on, show them which missions are affected and
   require confirmation.
2. **Flag and notify**: recompute coverage for affected missions on save and surface
   an explicit "at risk since approval" state to the lead (dashboard + staffing
   panel), rather than relying on someone happening to look.

A snapshot alternative (freeze proficiency as-at-acceptance on the assignment) gives
auditability but lets missions run on stale data, which is worse than the honest
warning.
