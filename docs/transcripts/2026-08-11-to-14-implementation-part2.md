# Transcript: 2026-08-11-to-14-implementation (part 2/2)

## 🧑 User — 2026-08-12 04:50

<task-notification>
<task-id>ae78d7d8380e6dcf8</task-id>
<tool-use-id>toolu_01JMPVbq5Dq4yqFRxdWT6Bv8</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/ae78d7d8380e6dcf8.output</output-file>
<status>completed</status>
<summary>Agent "Re-review Task 4.3 fix round 1" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>### Finding Verdicts

- **Important — residual `IntegrityError` → 500 on a concurrent duplicate proposal.** ADDRESSED — `backend/mission_control/missions/services/assignments.py:82-98` wraps each `full_clean()`/`save()` pair in a nested `with transaction.atomic():` (a savepoint, since it nests inside the outer `@transaction.atomic` on `assignments_propose`), and `except IntegrityError:` re-raises `ApplicationError(f"{user.name} was just assigned to this mission by someone else.") from None`. Verified against Django's actual transaction internals (`Model.save()` wraps its write in `transaction.mark_for_rollback_on_error`, which sets `connection.needs_rollback` the instant the `IntegrityError` occurs, independent of any manual try/except; `Atomic.__exit__` then performs a real `savepoint_rollback`/`rollback` on any exception propagating through it). Because the `except` clause re-raises immediately with no further queries in between, the outer `@transaction.atomic` decorator alone would in fact have recovered cleanly even without the added savepoint — but the savepoint is the textbook-correct, zero-downside pattern the finding explicitly allowed ("a savepoint if needed"), and bulk propose remains genuinely all-or-nothing (the re-raised `ApplicationError` unwinds the entire outer atomic block, rolling back any earlier users created in the same call). Covering test `test_propose_concurrent_duplicate_returns_400_not_500` (`backend/tests/missions/test_assignment_apis.py:129-167`) patches `Assignment.save` to unconditionally raise the real `IntegrityError` message, so it exercises the INSERT-level failure genuinely (not merely re-testing the pre-check), asserts 400 with a proper `{message, extra}` envelope, asserts zero half-written rows, and proves the transaction isn't poisoned by successfully retrying in the same test (same pytest-django transaction scope). The broad `except IntegrityError` is acceptable here — `Assignment.Meta.constraints` (`backend/mission_control/missions/models.py:99-106`) defines only the one partial-unique constraint, so there's no other realistic `IntegrityError` source on this model that the catch could misreport.
- **Coverage gap 1 (non-`CREW_MEMBER` rejection untested)** — ADDRESSED. `test_propose_non_crew_role_rejected` (`backend/tests/missions/test_assignment_apis.py:170-179`) proposes a `MISSION_LEAD` id (default `is_active=True`, so distinct from the `is_active` half) and asserts 400.
- **Coverage gap 2 (re-propose after `declined` untested)** — ADDRESSED. `test_reproposing_after_decline_is_allowed_via_api` (`:182-203`) propose → decline via `/respond/` → re-propose; asserts 201 and exactly one `proposed` row.
- **Coverage gap 3 (terminal-mission guards untested)** — ADDRESSED. `test_propose_on_terminal_mission_rejected` and `test_respond_on_terminal_mission_rejected` (`:206-227`), both parametrized over `COMPLETED`/`CANCELLED`, assert 400 for `assignments_propose` and `assignment_respond` respectively.
- **Coverage gap 4 (no cross-tenant 404 for `AssignmentRemoveApi`)** — ADDRESSED. `test_cross_tenant_assignment_remove_404` (`:230-234`) asserts 404 for a same-tenant lead posting to another tenant's assignment's `/remove/`.

### New Breakage in the Fix Diff
None. The diff is scoped exactly to `services/assignments.py`'s create loop and new tests; no other files touched, `common/exception_handler.py` untouched (consistent with fixing at the service boundary rather than globally), `assignment_remove`/`assignment_respond` unchanged, no regression risk to the sequential `ValidationError` path (only `IntegrityError` is caught; `full_clean()`'s `ValidationError` still propagates through the nested `atomic()` unmolested).

### Out-of-Scope Observations
None.

### Verdict
**Fix round:** All findings addressed, no new Critical/Important breakage.</result>
<usage><subagent_tokens>79643</subagent_tokens><tool_uses>15</tool_uses><duration_ms>449215</duration_ms></usage>
</task-notification>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ sed -n '160,175p' docs/superpowers/specs/2026-08-11-mission-control-design.md`

<details><summary>⤷ Bash result</summary>

```
| `activate` | approved → active | `MISSION_PROGRESS` | `start_date <= today`; re-runs conflict check (belt and braces) |
| `complete` | active → completed | `MISSION_PROGRESS` | `end_date <= today` |
| `cancel` | any non-terminal → cancelled | `MISSION_PROGRESS` | Reason required; live assignments flip to `removed` |

Activation and completion are explicit actions; the UI nudges when a mission is due (no scheduler in v1).

## 9. Assignments, availability & coverage

**Assignment FSM:** `propose
… [467 more chars — see the .jsonl]
```

</details>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ cat >> .superpowers/sdd/00-overview/progress.md <<'EOF' ⏎ Task 4.3: fix round 1/5 (5 addressed, 0 open; commits b8eb8f4..0224bcb) ⏎ Task 4.3: complete (commits
… [1,357 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
ok
```

</details>

- 🔧 **Agent** · `prompt=You are implementing Task 4.4: Wire the staffing guard into the FSM. ⏎  ⏎ This is task 25 of 33 in the build of "Mission Control", a multi-tenant Django+DRF / React SPA product. Stages 1-3 are complete. Task 4.1 a
… [8,991 more chars — see the .jsonl]`

<details><summary>⤷ Agent result</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: a2ddacd6bc885b25b (internal ID - do not mention to user. Use SendMessage with to: 'a2ddacd6bc885b25b', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do
… [580 more chars — see the .jsonl]
```

</details>

### 🤖 Assistant — 2026-08-12 04:51

**Task 4.3 done** (`0224bcb`, review clean) — 24/33, backend at **301 tests**.

Task 4.4 is running with a ruling I settled from the spec rather than letting it inherit a default: `approve` and `activate` need *different* guards. Spec §8 says activate only "re-runs conflict check (belt and braces)", so pointing both at the full staffing validation would block an approved mission from activating just because a crew member declined afterwards. It also carries the cascade-delete test that Task 4.1's review flagged as untested anywhere in the suite.

## 🧑 User — 2026-08-12 05:04

<task-notification>
<task-id>a2ddacd6bc885b25b</task-id>
<tool-use-id>toolu_011hBNjxCsgoseHUtz9NPYuV</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/a2ddacd6bc885b25b.output</output-file>
<status>completed</status>
<summary>Agent "Implement Task 4.4: wire staffing guard into FSM" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>**Status:** DONE

Commit: `ec54360` — "feat: approve/activate staffing guard with crew-row locking; cancel removes live assignments"

Test summary: full backend suite 309/309 passed (301 pre-existing + 8 new), `ruff check .` clean.

Approve runs full `staffing_validation_errors` (coverage + crew bounds + conflicts); activate runs only the new `mission_conflict_errors` (conflicts-only, belt-and-braces per spec §8) — deliberately split so a crew member removed/declined after approval doesn't block activation. Cancel flips live assignments to `removed` inside the same atomic transaction as the status write and audit row, proven by fault-injection test (not just happy-path assertion). Added the cascade-delete test inherited from Task 4.1's review (Mission/User delete with assignments, exercising the composite-FK-vs-CASCADE interaction).

Concern: the brief's Step 3b said only 2 `test_fsm.py` tests needed staffing updates; actually 6 did (the others weren't listed but reach a successful approve/activate). I fixed all 6 and documented this discrepancy in the report — flagging in case the controller wants to correct the brief for future reference.

Report: `/Users/samrichards/code/mission-control-mutinex/.superpowers/sdd/00-overview/task-4.4-report.md`</result>
<usage><subagent_tokens>132203</subagent_tokens><tool_uses>72</tool_uses><duration_ms>739978</duration_ms></usage>
</task-notification>

- 🔧 **Bash** · `command="/Users/samrichards/.claude/plugins/cache/claude-plugins-official/superpowers/6.2.0/skills/subagent-driven-development/scripts/review-package" /Users/samrichards/code/mission-control-mutinex/docs/superpowers/plan
… [59 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
wrote /Users/samrichards/code/mission-control-mutinex/.superpowers/sdd/00-overview/review-0224bcb..ec54360.diff: 1 commit(s), 26159 bytes
```

</details>

- 🔧 **Agent** · `prompt=You are reviewing one task's implementation: first whether it matches its requirements, then whether it is well-built. This is a task-scoped gate, not a merge review — a broad whole-branch review happens separatel
… [8,199 more chars — see the .jsonl]`

<details><summary>⤷ Agent result</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: ad23b3ef9fdce17b3 (internal ID - do not mention to user. Use SendMessage with to: 'ad23b3ef9fdce17b3', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do
… [580 more chars — see the .jsonl]
```

</details>

### 🤖 Assistant — 2026-08-12 05:05

Task 4.4 committed (`ec54360`, 309/309). The implementer had to modify six existing FSM tests rather than the two the brief predicted — that's exactly where a regression hides, so I've told the reviewer to scrutinise each change and judge whether it reflects genuinely new correct behaviour or an assertion weakened to make a failure go away. Reviewing on the stronger model.

## 🧑 User — 2026-08-12 05:11

<task-notification>
<task-id>ad23b3ef9fdce17b3</task-id>
<tool-use-id>toolu_01HJuGZR6fLQyri5rfWBVCzs</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/ad23b3ef9fdce17b3.output</output-file>
<status>completed</status>
<summary>Agent "Review Task 4.4 (spec + quality)" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>### Spec Compliance

- ✅ Spec compliant on every requirement the diff can prove, with two verification gaps noted below.
- **Guard split is real and correct.** `approve` → `_validate_staffing_for_approval` → `staffing_validation_errors` (coverage + bounds + conflicts) at `services/missions.py:89-100`; `activate` → `_validate_conflicts_for_activation` → `mission_conflict_errors` **only** at `services/missions.py:103-121`, wired at `services/missions.py:128` and `:133`. The activate guard provably does not enforce coverage or crew bounds — I ran three focused tests (scratchpad, not added to the repo) against this checkout: activate succeeds after the sole accepted crew member is flipped to `declined` post-approval; activate succeeds after `max_crew` is exceeded post-approval; activate is blocked when a competing mission is approved in the interim (error names "Ada"). 3 passed.
- **No re-derivation of the availability rule.** The only new query, `selectors/staffing.py:239-266`, calls `_hard_block_qs(...)` with `exclude_mission_id=mission.id` (`:253`) and narrows by `_accepted_assignments_qs(mission).values("user_id")` (`:255`), so the `user__is_active=True` ruling from Task 4.2 and the §9 status set both come from the selector. Grepped the diff for `start_date__lte`, `end_date__gte`, a literal `{approved, active}` set and a hand-rolled overlap: none outside the pre-existing `_overlapping`/`_hard_block_qs`. `soft_conflicts_for_users` is not consumed here, so its absent-key contract is not in play.
- **`staffing_validation_errors` refactor is behaviour-preserving** — the extracted block is byte-identical and re-attached via `errors.extend(...)` at `selectors/staffing.py:299`; existing coverage at `tests/missions/test_staffing.py:620,625` still exercises the conflict text through the full function.
- **Cancel cascade** at `services/missions.py:174-187` is inside the same `@transaction.atomic` (`:141`), after the status write and `MissionTransition.objects.create`, no nested `atomic()`, single `.update()` over `LIVE_ASSIGNMENT_STATUSES` (= `{proposed, accepted}`, `missions/models.py:86`). `declined`/`removed` are untouched, asserted at `test_approval_guard.py:87-89`. The `assignment_live_uniq` reasoning in the comment is correct: `missions/models.py:100-105` is partial on `status__in=["proposed","accepted"]`, so moving rows *out* of the live set cannot collide.
- **FSM properties survive.** `select_for_update` re-read at `:149` still precedes every check; guards still run before the status write (`:161`); illegal-transition and reason checks unchanged; `PermissionDenied` vs `ApplicationError` split unchanged. `ApplicationError("Mission staffing is not valid.", extra={"errors": [...]})` reaches the client as `{"message": ..., "extra": {"errors": [...]}}` with status 400 — verified at `common/exception_handler.py:17-21`.
- **The 6 `test_fsm.py` changes are pure additions.** Every hunk in that file adds only a `staff(mission)` call plus the helper and its imports; there is not a single `-` line outside the import block, so no assertion was removed, loosened, or retargeted. `test_failed_guard_leaves_no_trace` (`tests/missions/test_fsm.py:262-270`) was correctly left alone — it fails on the missing `reject` reason, which is checked before `_run_guards`, so it still fails for its original reason rather than being silently absorbed by the new guard. `test_invalid_state_transition` likewise still hits the state check before any guard. The brief's claim of 2 affected tests is indeed wrong: `MissionFactory.min_crew = 1` (`missions/factories.py:20`), so every successful approve now needs an accepted crew member — 6 is the right number. No test outside `test_fsm.py` performs a successful approve/activate (grepped `tests/` — the only other hit is `test_mission_apis.py:185`, which asserts the illegal-transition 400).
- **Cascade-delete tests are genuine**, not trivial passes: the composite FKs are `DEFERRABLE INITIALLY IMMEDIATE`, so if Django's collector emitted the parent delete before the dependent `Assignment` rows, `assignment_tenant_mission_fk`/`assignment_tenant_user_fk` would raise inside the statement. `test_assignment_model.py` also picks a user who is only the assignment's crew member (never a `created_by`, which is `PROTECT`), so the CASCADE path is reached rather than short-circuited.
- ⚠️ **Cannot verify from diff:** the reported RED/GREEN transcript and the 309-passed full-suite figure. I ran only the three focused split tests above.
- ⚠️ **Cannot verify from diff:** concurrent behaviour of the new row lock — no test exercises two simultaneous transactions (see Minor below).
- **Scope:** no staffing-panel UI, no my-assignments UI, no matching logic. Clean.

### Strengths

- The controller ruling was not just implemented but reasoned about in the code: the docstring at `services/missions.py:103-117` states *why* activate is narrower, so the next person cannot "fix" it back by accident.
- Extracting `mission_conflict_errors` into the selector rather than inlining a conflict query in the service is the right call — the rule stays in one module, and the new entry point is a thin slice of the existing one, not a parallel implementation.
- The implementer caught and fixed the brief's undercount of affected FSM tests instead of patching only the two named and leaving four red, and disclosed it.
- The fault-injection cancel test does discriminate against a plausible wrong implementation (an `on_commit` hook would never fire under `django_db`, failing `pytest.raises`).

### Issues

#### Critical (Must Fix)

None.

#### Important (Should Fix)

1. **`services/missions.py:86` — lock rows are acquired in non-deterministic order; two concurrent approvals sharing crew can deadlock.**
   `list(User.objects.select_for_update().filter(id__in=accepted_user_ids))` has no `ORDER BY`, and `User` declares no `Meta.ordering` (`users/models.py:29-32`; `BaseModel.Meta` is `abstract` only). Postgres locks rows in scan order, and the plan for `id IN (...)` can differ between an index scan (id order) and a bitmap heap scan (physical order) depending on list size and statistics. Two transactions approving missions that share two or more crew members can therefore acquire `u5`/`u9` in opposite orders and deadlock — which is precisely the contention scenario this lock was added for. The loser gets `DeadlockDetected`, which is not an `ApplicationError` and not a DRF exception, so `common/exception_handler.py:19` returns `None` and it surfaces as a 500. Fix: `.filter(id__in=accepted_user_ids).order_by("id")` — the `LockRows` node sits above `Sort`, so rows are locked in sorted order. The mission-row lock at `:149` is taken first in every path and no other service takes row locks (grepped: `select_for_update` appears at only these two sites), so cross-table ordering is fine; this is purely intra-statement ordering.

2. **The guard split — the deliverable of this task — has zero test coverage.**
   `tests/missions/test_approval_guard.py` contains six tests (`:33,:40,:49,:66,:75,:92`); none of them activates anything. `mission_conflict_errors` has no direct test in `tests/missions/test_staffing.py` either (grepped: only `staffing_validation_errors` is imported there). Consequently, reverting `services/missions.py:133` to `_validate_staffing_for_approval` — the exact regression the controller ruling exists to prevent — leaves all 61 FSM tests and all 6 approval-guard tests green. I confirmed the behaviour is correct today by running the three tests described above, so this is a durability gap, not a defect; but the task cannot be trusted to *stay* correct without them. Add at least: activate succeeds after a post-approval decline/removal, and activate fails when a competing mission is approved in the interim.

#### Minor (Nice to Have)

3. **`services/missions.py:81-86` re-derives "this mission's accepted crew" instead of using the selector.** `_accepted_assignments_qs` (`selectors/staffing.py:129-154`) is the canonical definition and filters `user__is_active=True`; the lock helper's copy does not. The difference is a harmless superset for locking, but it is a second definition of the same set living in the service layer (reads belong in selectors). Prefer locking off `_accepted_assignments_qs(mission).values_list("user_id", flat=True)`.

4. **`services/missions.py:86` — `User.objects` is not tenant-filtered.** Safe here because the ids come from the tenant-scoped `Assignment.objects` query on the line above, but it diverges from the established interface fact ("any code that lists or looks up users MUST filter by tenant explicitly") and from the codebase's own precedent at `services/assignments.py:38-44`, which adds `tenant_id=` with a comment saying the filter is load-bearing. Adding `tenant_id=mission.tenant_id` costs nothing and removes the question.

5. **Local imports are justified by a cycle that does not exist.** `selectors/staffing.py:22-36` imports only models — nothing from `services` — and `Assignment`/`AssignmentStatus`/`LIVE_ASSIGNMENT_STATUSES` come from `missions.models`, which `services/missions.py:8-13` already imports at module top. The function-local imports at `:78-79`, `:95`, `:116`, `:180-184` are therefore dead weight on a hot path. Plan-mandated (the brief's Step 3 sample asserts the cycle), so logging it as the rubric requires rather than as an implementer error.

6. **`services/missions.py:107-110` docstring is inaccurate about how coverage can regress.** It says coverage/bounds "cannot silently regress except via `assignment_remove`", but deactivating a crew member also drops them from `_accepted_assignments_qs` (`selectors/staffing.py:152`) and hence from `filled_count`/`accepted_count` — the Task 4.2 human ruling. This strengthens the case for the split rather than weakening it, but the comment as written is wrong and will mislead.

7. **`test_approval_guard.py:92-115` proves only one direction of cancel atomicity.** The fault is injected *before* the cascade write (`monkeypatch.setattr(Assignment.objects, "filter", boom)` at `:105`), so it proves the status write and audit row roll back when a later statement fails; it does not prove that a failure *after* the cascade rolls the cascade back, and `:115`'s "assignment still ACCEPTED" assertion is vacuous because the update never ran (the test's own docstring implies otherwise). A second injection after the cascade — or patching `MissionTransition.objects.create` to fail on a cancel, with the cascade reordered ahead of it — would close it. Structurally the property holds (plain `.update()` inside the outer atomic, no savepoint).

8. **`test_competing_approval_loses_shared_crew` (`:49`) is sequential, not concurrent** — it proves the conflict *check*, not the row lock. The locking added by this commit has no test at all. Real concurrency tests need `TransactionTestCase`-style threading and are costly; noting it so the gap is on the record rather than proposing it as required work.

9. **No API-level test that a staffing failure produces the 400 envelope.** I traced the path by reading `common/exception_handler.py:17-21` and it is correct, but nothing asserts `resp.data == {"message": "Mission staffing is not valid.", "extra": {"errors": [...]}}` end to end; `test_mission_apis.py:180-188` only covers the illegal-transition message.

### Assessment

**Task quality:** Approved with follow-ups (issues 1 and 2 before this is depended on by Stage 5/6)

**Reasoning:** The controller's guard split is implemented exactly as ruled and empirically verified — activate is conflicts-only, tolerates post-approval crew loss, and still catches interim conflicts — with no restatement of the availability rule and no weakened FSM assertions in the six modified tests. The two things to fix are an unordered `SELECT ... FOR UPDATE` that can deadlock under the very contention it was added to serialize, and the absence of any test pinning the split itself.</result>
<usage><subagent_tokens>80758</subagent_tokens><tool_uses>24</tool_uses><duration_ms>375616</duration_ms></usage>
</task-notification>

- 🔧 **SendMessage** · `{"to": "a2ddacd6bc885b25b", "summary": "Task 4.4 fix round 1: deadlock risk + untested split", "message": "Task 4.4 review came back with two Important findings. Fix both plus the cheap items listed after them, re-run th
… [4,593 more chars — see the .jsonl]`

<details><summary>⤷ SendMessage result</summary>

```
{"success":true,"message":"Agent \"a2ddacd6bc885b25b\" had no active task; resumed from transcript in the background with your message. You'll be notified when it finishes. Output: /private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/a2ddacd6bc885b25b.output","resumedAgentId":"a2ddacd6bc885b25b","pin":{"id":"a2ddacd6bc885b25b","name":"a2ddacd6bc885b25b","ref":"8ec7f7"}}
```

</details>

### 🤖 Assistant — 2026-08-12 05:11

That reviewer did unusually good work — it wrote three throwaway tests against the checkout to empirically confirm the approve/activate split behaves correctly, and verified all six modified FSM tests were pure additions with no weakened assertions.

It found two things worth fixing. The row lock added for concurrent approvals has no `ORDER BY`, so two transactions approving missions that share crew can lock the same users in opposite orders and deadlock — surfacing as a 500, under exactly the contention the lock was added to handle. And the guard split itself has no test: reverting it would leave all 61 FSM tests green. Both are in the fix round, with a mutation check required on the new tests.

## 🧑 User — 2026-08-12 05:18

<task-notification>
<task-id>a2ddacd6bc885b25b</task-id>
<tool-use-id>toolu_01JiqDp3vESXMJgxvbqyHWwi</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/a2ddacd6bc885b25b.output</output-file>
<status>completed</status>
<summary>Agent "Implement Task 4.4: wire staffing guard into FSM" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>**Status:** DONE

Commits: `1f64229` — "fix: deterministic crew-row lock order and pin the approve/activate guard split" (on top of `ec54360`)

Test summary: full backend suite 311/311 passed, `ruff check .` clean repo-wide; mutation check confirmed the new activate-split tests actually pin the behavior.

Both Important findings fixed: `.order_by("id")` closes the deadlock window in `_lock_accepted_crew`; two new tests directly cover the approve/activate guard split (post-approval coverage loss doesn't block activation, a fresh interim conflict does), verified by temporarily reverting the guard and confirming the new test fails, then restoring. All four small items fixed: lock now sources crew from `_accepted_assignments_qs`, `User` query is tenant-filtered, the inaccurate docstring is corrected, and the cancel-atomicity test now lets the real `UPDATE` execute before injecting the fault.

Report: `/Users/samrichards/code/mission-control-mutinex/.superpowers/sdd/00-overview/task-4.4-report.md`</result>
<usage><subagent_tokens>158417</subagent_tokens><tool_uses>30</tool_uses><duration_ms>377281</duration_ms></usage>
</task-notification>

- 🔧 **Bash** · `command="/Users/samrichards/.claude/plugins/cache/claude-plugins-official/superpowers/6.2.0/skills/subagent-driven-development/scripts/review-package" /Users/samrichards/code/mission-control-mutinex/docs/superpowers/plan
… [59 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
wrote /Users/samrichards/code/mission-control-mutinex/.superpowers/sdd/00-overview/review-ec54360..1f64229.diff: 1 commit(s), 13499 bytes
```

</details>

- 🔧 **Agent** · `prompt=You are re-reviewing one task's fix round. A previous review produced findings; an implementer has attempted to fix them. Your job is to verdict each finding and inspect the fix diff — nothing else. ⏎  ⏎ ## The Ta
… [5,594 more chars — see the .jsonl]`

<details><summary>⤷ Agent result</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: ab8cee4b7838e9d3f (internal ID - do not mention to user. Use SendMessage with to: 'ab8cee4b7838e9d3f', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do
… [580 more chars — see the .jsonl]
```

</details>

### 🤖 Assistant — 2026-08-12 05:18

Task 4.4 fixes committed (`1f64229`, 311/311), with the mutation check confirming the new tests actually pin the guard split. Re-review running — I've asked it to verify the "activate succeeds after crew loss" test constructs a state where the *full* validation would genuinely fail, otherwise it would pass under either guard and prove nothing.

## 🧑 User — 2026-08-12 05:21

<task-notification>
<task-id>ab8cee4b7838e9d3f</task-id>
<tool-use-id>toolu_01HQxPA3cAzivQ2VX8sMupmH</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/ab8cee4b7838e9d3f.output</output-file>
<status>completed</status>
<summary>Agent "Re-review Task 4.4 fix round 1" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>## Finding Verdicts

- **Important 1 — crew row lock can deadlock (no `ORDER BY`)** — ADDRESSED. `backend/mission_control/missions/services/missions.py:100-103`: `User.objects.select_for_update().filter(id__in=accepted_user_ids, tenant_id=mission.tenant_id).order_by("id")`. Postgres places `LockRows` above `Sort` in the plan, so this fixes lock-acquisition order deterministically for any two transactions calling `_lock_accepted_crew` (shared by both `approve` and `activate`), closing the deadlock/500 path.

- **Important 2 — guard split has no test** — ADDRESSED. Two new tests added at `backend/tests/missions/test_approval_guard.py:89-117`: `test_activate_succeeds_despite_post_approval_coverage_loss` (crew flipped to `DECLINED` post-approval, asserts `activate` still succeeds) and `test_activate_blocked_by_conflict_from_mission_approved_in_interim` (competitor mission holding the same crew member approved with overlapping dates, asserts `activate` fails). The first genuinely distinguishes the two guards: with the accepted crew declined, `_accepted_assignments_qs` returns empty, so full validation (`staffing_validation_errors`) would raise a coverage error ("Requirement Piloting ≥5 needs 1, has 0") that the conflicts-only path never runs. The mutation-check narrative in the report (activate temporarily pointed at `_validate_staffing_for_approval`, `-k "activate"` selects exactly 2 of the 8 tests in the file, 1 failed/1 passed, `6 deselected`) is internally consistent with the file's actual test count and names — credible.

- **Small 3 — lock should source ids from `_accepted_assignments_qs`** — ADDRESSED. `backend/mission_control/missions/services/missions.py:93,96-98`: imports and calls `_accepted_assignments_qs(mission).values_list("user_id", flat=True)`. Still produces `SELECT ... FROM users ... FOR UPDATE` over `User` rows (ids feed a `User.objects...filter(id__in=...)`), not an accidental no-op or wrong-table lock. Narrowing to `user__is_active=True` doesn't leave a correctness gap: every downstream guard read (`mission_coverage`, `mission_conflict_errors`) also sources its "this mission's accepted crew" set from the same selector, so no row the guard depends on is left unlocked.

- **Small 4 — lock not tenant-filtered** — ADDRESSED. `backend/mission_control/missions/services/missions.py:101`: `.filter(id__in=accepted_user_ids, tenant_id=mission.tenant_id)`.

- **Small 5 — docstring wrongly claims coverage "cannot silently regress except via `assignment_remove`"** — ADDRESSED at the cited location but incompletely fixed overall. `backend/mission_control/missions/services/missions.py:124-133` now correctly names both regression paths (assignment_remove and deactivation). However the *identical* wrong claim still exists, untouched, in `backend/mission_control/missions/selectors/staffing.py:274-277` (`staffing_validation_errors` docstring: "coverage/crew-bounds cannot regress between approval and activation without going through `assignment_remove`, which is a lead/director action independent of the FSM"). This file was not touched by the fix diff. The codebase now has two docstrings making contradictory claims about the same regression path.

- **Small 6 — cancel-atomicity test's fault injection was vacuous** — ADDRESSED. `backend/tests/missions/test_approval_guard.py:159-178`: now monkeypatches `QuerySet.update` itself so the real cascade update executes (writing `removed` inside the open transaction) before raising. Verified `Model.save()` uses the internal `QuerySet._update()` method, not the patched public `update()`, so this patch only intercepts the cascade's explicit `.filter(...).update(...)` call — the assertion is genuinely non-vacuous.

## New Breakage in the Fix Diff

None at Critical/Important severity. One minor documentation inconsistency (not a behavioral bug): `backend/mission_control/missions/selectors/staffing.py:274-277` now disagrees with the corrected docstring in `services/missions.py:124-133` on the same factual point (see Small 5 above) — a reviewer/future maintainer reading only `staffing.py` would still be told the old, wrong thing.

## Out-of-Scope Observations

None.

## Verdict

**Fix round:** All findings addressed, no new Critical/Important breakage — Small 5 is addressed at its cited location but leaves a duplicate, now-contradicting docstring in `selectors/staffing.py:274-277` uncorrected; worth a follow-up but does not block.</result>
<usage><subagent_tokens>59867</subagent_tokens><tool_uses>6</tool_uses><duration_ms>150729</duration_ms></usage>
</task-notification>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ sed -n '30,100p' backend/mission_control/missions/apis/assignments.py`

<details><summary>⤷ Bash result</summary>

```
coverage = mission_coverage(mission)
    roster_assignments = list(mission_selectors.mission_assignments(mission))
    user_ids = [a.user_id for a in roster_assignments]

    soft_conflicts = soft_conflicts_for_users(
        user_ids=user_ids,
        start_date=mission.start_date,
        end_date=mission.end_date,
        exclude_mission_id=mission.id,
    )
    blocked = hard_blocked_user_ids(
        start_date=mission.start_date, end_date=mission.end_date, exclude_mission_id=mission.id
… [2,036 more chars — see the .jsonl]
```

</details>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ cat >> .superpowers/sdd/00-overview/progress.md <<'EOF' ⏎ Task 4.4: fix round 1/5 (6 addressed, 0 open; commits ec54360..1f64229) ⏎ Task 4.4: complete (commits
… [2,458 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
ok
```

</details>

- 🔧 **Agent** · `prompt=You are implementing Task 4.5: Frontend — staffing panel. ⏎  ⏎ This is task 26 of 33 in the build of "Mission Control", a multi-tenant Django+DRF / React SPA product. The backend is complete through Stage 4's writ
… [8,471 more chars — see the .jsonl]`

<details><summary>⤷ Agent result</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: a52a00ddda0105193 (internal ID - do not mention to user. Use SendMessage with to: 'a52a00ddda0105193', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do
… [580 more chars — see the .jsonl]
```

</details>

### 🤖 Assistant — 2026-08-12 05:22

**Task 4.4 done** (`1f64229`, review clean) — 25/33, backend at **311 tests**. The staffing guard is now wired into the FSM with the approve/activate split pinned by a mutation-checked test, and the deadlock window closed.

Task 4.5 (staffing panel UI) is running. The one thing I've emphasised: `hard_blocked` must render as blocking and `soft_conflicts` as a non-blocking warning — inverting those is the highest-value mistake available in this task.

## 🧑 User — 2026-08-12 05:31

<task-notification>
<task-id>a52a00ddda0105193</task-id>
<tool-use-id>toolu_01TTit4LYRbeynbknwed4Msj</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/a52a00ddda0105193.output</output-file>
<status>completed</status>
<summary>Agent "Implement Task 4.5: staffing panel UI" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>Committed successfully.

**Status:** DONE
- Commit: `2ef7c28` — feat: staffing panel with coverage bars, conflict chips, crew management
- Tests: 56/56 pass (49 prior + 7 new), `npm run build` succeeds, `npm run lint` clean of new warnings
- No concerns
- Report: `/Users/samrichards/code/mission-control-mutinex/.superpowers/sdd/00-overview/task-4.5-report.md`</result>
<usage><subagent_tokens>152689</subagent_tokens><tool_uses>71</tool_uses><duration_ms>575208</duration_ms></usage>
</task-notification>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ OUT=.superpowers/sdd/00-overview/review-1f64229..2ef7c28.diff ⏎ { ⏎   echo "# Review package: 1f64229..2ef7c28" ⏎   echo; echo "## Commits"; git log --oneline
… [216 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
31376 .superpowers/sdd/00-overview/review-1f64229..2ef7c28.diff
```

</details>

- 🔧 **Agent** · `prompt=You are reviewing one task's implementation: first whether it matches its requirements, then whether it is well-built. This is a task-scoped gate, not a merge review — a broad whole-branch review happens separatel
… [7,718 more chars — see the .jsonl]`

<details><summary>⤷ Agent result</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: af7c76d718ef1c652 (internal ID - do not mention to user. Use SendMessage with to: 'af7c76d718ef1c652', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do
… [580 more chars — see the .jsonl]
```

</details>

### 🤖 Assistant — 2026-08-12 05:32

Task 4.5 committed (`2ef7c28`, 56 frontend tests, build clean). Review running, with the hard-block vs soft-conflict treatment as the first thing it must adjudicate.

## 🧑 User — 2026-08-12 05:35

<task-notification>
<task-id>af7c76d718ef1c652</task-id>
<tool-use-id>toolu_01B5Cnsdf9qAhjKrpRarTT6Q</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/af7c76d718ef1c652.output</output-file>
<status>completed</status>
<summary>Agent "Review Task 4.5 (spec + quality)" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>### Spec Compliance
- ✅ Spec compliant with one Important gap in test evidence (see below). All required interfaces from the brief are present and correctly wired: `StaffingSchema`, `useStaffing`/`useProposeAssignments`/`useRemoveAssignment` with correct query keys and invalidation, `MyAssignmentSchema`/`useMyAssignments`/`useRespondAssignment` produced per the Interfaces contract for Task 4.6, `staffing-panel.tsx` and `add-crew-dialog.tsx` built to spec, mission-detail-page wiring, mocks.ts extension.
- ⚠️ Cannot verify from diff: whether `roster` from the real backend ever contains statuses other than `proposed`/`accepted` (the badge-variant mapping at `staffing-panel.tsx:383` only distinguishes `accepted` vs. everything-else). The implementer's report claims they read `backend/mission_control/missions/selectors/staffing.py` directly and confirmed the selector only returns live assignments — plausible, but backend source isn't in this diff. Low risk if true.

### Strengths
- **The one thing that mattered most is correct.** `hard_blocked` → `Badge variant="destructive"` "Unavailable" (`staffing-panel.tsx:407`), `soft_conflicts` → amber outline "Conflict" badge in a `Popover` listing each conflict (`staffing-panel.tsx:386-403`). The two are independent JSX conditionals, not mutually exclusive branches, so they render together correctly on inspection. Neither disables any control — matches the "surfaced, not blocking" requirement exactly.
- Coverage is rendered as authoritative, never recomputed: `accepted_count`, `min_crew`/`max_crew`, `fully_covered`, `filled_count`/`required_count` are all displayed straight from the server payload (`staffing-panel.tsx:337-364`); only the progress-bar *percentage* is derived, purely for rendering width, clamped to 100.
- Both write paths (`add-crew-dialog.tsx`, per-row remove) are gated on `assignment.manage` via the shared `hasPermission`/`useUser` helpers (`staffing-panel.tsx:304,311,370,408`), and this is the one behavior with a dedicated permission test (`staffing.test.tsx:610-623`).
- Mutation invalidation keys are correct and verified against the real query key: `invalidateStaffing` invalidates `["missions", missionId, "staffing"]` and `["missions", missionId]` (`assignments.ts:97-100`); confirmed `useMission`'s actual queryKey is `["missions", id]` (`frontend/src/features/missions/api/missions.ts:73`) — the invalidation target is a real match, not a guess.
- `errorMessage`/`fieldErrorsFrom` reused, not copied (`add-crew-dialog.tsx:197`, `staffing-panel.tsx:303`); `errorMessage` correctly passes through a business-rule 400's specific message unmodified (`api-errors.ts:27-42`), so a hard-block refusal message would render intelligibly if it were exercised.
- Query branch order (`isLoading` → `isError` w/ `role="alert"` → data) followed correctly in both `staffing-panel.tsx:315-324` and `add-crew-dialog.tsx:255-260`.
- Candidate picker correctly excludes current roster (`add-crew-dialog.tsx:226-227`, tested at `staffing.test.tsx:583-608`) and doesn't trigger any extra fetch on selection — pure local state.
- Zero-requirements and empty-roster states handled with real copy, not a blank card (`staffing-panel.tsx:342-343,376-377`).
- No Stage 5/6 or Task 4.6 UI present; `useMyAssignments`/`useRespondAssignment` exist only as the brief's specified interface surface, unconsumed — correctly scoped, not creep.
- Single MSW instance extended correctly, mutable `staffing` state reseeded in `resetMockData()` (`mocks.ts:750-757`), matching the established `skills`/`missions` pattern.

### Issues

#### Critical (Must Fix)
None.

#### Important (Should Fix)
- **The task's own "highest-value defect" path — a 400 refusal from propose or remove — has zero test coverage, despite the report claiming it was "confirmed."** `staffing.test.tsx` has 7 tests; none of them mock a non-2xx response from `POST /api/v1/missions/:id/assignments/` or `POST /api/v1/assignments/:id/remove/` (the mock handlers at `mocks.ts:783-813` always succeed). The report's self-review section states "Confirmed a 400 from propose surfaces the server's message (toast + inline); remove surfaces it via toast" — this is not backed by any test in the diff, only by static code reading. Given this review's explicit instruction to distrust the report and given the reviewing brief calls this exact scenario ("the server refuses hard-blocked proposals with a business-rule 400 — is that intelligible in the UI?") the single highest-value case to verify, this is a real gap: the wiring (`add-crew-dialog.tsx:235-245`, `staffing-panel.tsx:326-332`) looks correct on inspection but is unverified by any green test. Add at least one `server.use(http.post(".../assignments/", () =&gt; HttpResponse.json({message: "..."}, {status:400})))` test asserting the message renders inline and/or in a toast, and one equivalent for remove.

#### Minor (Nice to Have)
- No test exercises `hard_blocked: true` and `soft_conflicts` non-empty on the *same* roster entry simultaneously — the code (`staffing-panel.tsx:386,407`) is two independent conditionals so this is very likely fine, but the report's phrasing ("verified... and a separate test for the reverse") could be read as claiming this combination was tested when it wasn't; only two single-condition cases exist (`staffing.test.tsx:543-565` covers hard-blocked-only, test 1 covers conflict-only).
- `removeAssignment.isPending` (`staffing-panel.tsx:413`) disables every row's Remove button while any one removal is in flight, not just the clicked row's — acceptable but a small UX rough edge for a roster with several rows.
- Progress bar has `role="progressbar"`/`aria-valuenow` but no `aria-valuemin`/`aria-valuemax` (`staffing-panel.tsx:353`) — trivial a11y completeness gap.
- Mutation responses (`StaffingSchema`, the full updated payload) are parsed and then discarded in favor of an invalidate+refetch (`assignments.ts:102-120`); this is spec-mandated by the brief's Interfaces text ("mutations invalidate the staffing key"), so not a defect, but it's a free optimistic-update opportunity (`setQueryData` with the mutation's own response) left on the table, costing one extra round trip per write.

### Assessment
**Task quality:** Approved
**Reasoning:** The semantic core of this task — hard-block vs. soft-conflict treatment, permission gating, authoritative coverage rendering, correct invalidation keys verified against the real `useMission` query key — is implemented correctly and cleanly, in properly separated files matching bulletproof-react conventions. The one Important finding is a test-coverage gap on the propose/remove error path that the report overclaims as verified; the underlying code is correct on inspection, so this is fixable with a couple of added MSW-driven tests rather than a design change.</result>
<usage><subagent_tokens>59429</subagent_tokens><tool_uses>9</tool_uses><duration_ms>179441</duration_ms></usage>
</task-notification>

- 🔧 **SendMessage** · `{"to": "a52a00ddda0105193", "summary": "Task 4.5 fix round 1: untested 400 error path", "message": "Task 4.5 review came back Approved with one Important finding. Fix it plus the two cheap items below, re-run the tests c
… [3,466 more chars — see the .jsonl]`

<details><summary>⤷ SendMessage result</summary>

```
{"success":true,"message":"Agent \"a52a00ddda0105193\" had no active task; resumed from transcript in the background with your message. You'll be notified when it finishes. Output: /private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/a52a00ddda0105193.output","resumedAgentId":"a52a00ddda0105193","pin":{"id":"a52a00ddda0105193","name":"a52a00ddda0105193","ref":"8223ef"}}
```

</details>

### 🤖 Assistant — 2026-08-12 05:36

The staffing panel got the semantics right — the reviewer confirmed hard blocks render as blocking and soft conflicts as non-blocking warnings, as independent conditionals that don't exclude each other.

The gap it found is instructive: the report claimed the 400-refusal path was "confirmed", but that was static reading, not a test — and no mock ever returns a non-2xx. That path is how the panel's central rule actually reaches the user, so it's now being pinned with real MSW tests, and I've asked the implementer to correct the overclaim in its report.

## 🧑 User — 2026-08-12 05:39

<task-notification>
<task-id>a52a00ddda0105193</task-id>
<tool-use-id>toolu_01WNzW4kx6G1GsvQMZiS8EQQ</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/a52a00ddda0105193.output</output-file>
<status>completed</status>
<summary>Agent "Implement Task 4.5: staffing panel UI" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>**Status:** DONE
- Commits: `2ef7c28` feat: staffing panel with coverage bars, conflict chips, crew management; `77ac110` test: cover staffing propose/remove 400s, combined conflict chips, scoped remove-disable
- Tests: 60/60 pass (56 prior + 4 new: propose-400 inline, remove-400 toast, hard_blocked+soft_conflicts co-occurrence, scoped per-row disable), `npm run build` clean
- No concerns
- Report: `/Users/samrichards/code/mission-control-mutinex/.superpowers/sdd/00-overview/task-4.5-report.md` (fix report appended, self-review overclaim corrected in place)</result>
<usage><subagent_tokens>183932</subagent_tokens><tool_uses>22</tool_uses><duration_ms>217818</duration_ms></usage>
</task-notification>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ OUT=.superpowers/sdd/00-overview/review-2ef7c28..77ac110.diff ⏎ { ⏎   echo "# Review package: 2ef7c28..77ac110" ⏎   echo; echo "## Commits"; git log --oneline
… [216 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
10303 .superpowers/sdd/00-overview/review-2ef7c28..77ac110.diff
```

</details>

- 🔧 **Agent** · `prompt=You are re-reviewing one task's fix round. A previous review produced findings; an implementer has attempted to fix them. Your job is to verdict each finding and inspect the fix diff — nothing else. This is a smal
… [4,074 more chars — see the .jsonl]`

<details><summary>⤷ Agent result</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: a3980e6d8abb12e84 (internal ID - do not mention to user. Use SendMessage with to: 'a3980e6d8abb12e84', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do
… [580 more chars — see the .jsonl]
```

</details>

### 🤖 Assistant — 2026-08-12 05:40

Task 4.5 fix committed (`77ac110`, 60 frontend tests). Small test-only diff, so the re-review is on the cheapest model.

## 🧑 User — 2026-08-12 05:41

<task-notification>
<task-id>a3980e6d8abb12e84</task-id>
<tool-use-id>toolu_01EHCgGjFgK57YAWHb8hpi5C</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/a3980e6d8abb12e84.output</output-file>
<status>completed</status>
<summary>Agent "Re-review Task 4.5 fix round 1" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>**Important — the propose/remove 400 path had zero test coverage** — ADDRESSED, with file:line evidence.

The fix adds two MSW-override tests (`server.use(..., status: 400)`) with realistic `{"message": "...", "extra": {}}` bodies:
- `staffing.test.tsx:149-166`: "shows the server's message inline in the Add crew dialog when propose is refused" asserts the exact server text (`/unavailable for these dates: crew member/i`) appears inside the still-open dialog via `within(dialog).findByText(...)`, not a generic error placeholder.
- `staffing.test.tsx:168-188`: "shows the server's message via toast when removing a roster member is refused" asserts the exact server text (`/only proposed or accepted assignments can be removed/i`) via `screen.findByText(...)` (toast surface; comment confirms no inline slot for bare per-row Remove actions).

The self-review wording was also corrected: `staffing.test.tsx:234-242` added a "Correction (post-review)" bullet explicitly calling out that "Confirmed a 400 from propose..." was reasoned from code, not tested, and that the lesson is not to claim "confirmed" without a failing test that would catch the bug.

**Minor A — no test for hard_blocked + soft_conflicts simultaneously** — ADDRESSED, with file:line evidence.

`staffing.test.tsx:116-147`: "shows both chips at once when a roster member is hard-blocked and also has a soft conflict" sets up roster data with `hard_blocked: true` and `soft_conflicts: [{...}]` on the same entry, then asserts both chips independently: `expect(screen.getByText(/unavailable/i)).toBeInTheDocument()` and `expect(screen.getByText(/^conflict$/i)).toBeInTheDocument()`. Comment confirms the two conditionals are independent.

**Minor B — `removeAssignment.isPending` disabled every row's Remove button** — ADDRESSED, with file:line evidence.

Code change in `staffing-panel.tsx:26-31, 48-54, 76-77`:
- Added `const [removingId, setRemovingId] = useState&lt;number | null&gt;(null)` to track the specific assignment being removed.
- Set `removingId = assignmentId` before `mutateAsync`, cleared in `finally` block.
- Changed `disabled={removeAssignment.isPending}` to `disabled={removingId === entry.assignment_id}`.

Test `staffing.test.tsx:190-216`: "only disables the row being removed while its removal is in flight, not every row" uses a deferred promise to pause the removal mid-flight, clicks Remove on one row (Sam), asserts that button is disabled while a different row's (Priya's) stays enabled, then resolves and asserts re-enabling. This test would fail against the old `isPending` global-disable logic (all rows would disable together).

**New Breakage in the Fix Diff**

None. Code is syntactically clean; `waitFor` import added correctly; deferred promise pattern explained via comment; state management proper (set before mutation, cleared in finally); all test assertions specific (no generic error checks). The single-line conditional change (`removingId === entry.assignment_id`) is direct and correct.

**Out-of-Scope Observations**

None.

**Verdict**

**Fix round:** All findings addressed, no new Critical/Important breakage — the implementer correctly covered the 400 paths with message-text assertions at the right UI surfaces, added the combined-chip test, and scoped the per-row disable to track which assignment is being removed (backed by a test that would fail on the old global-disable code).</result>
<usage><subagent_tokens>29463</subagent_tokens><tool_uses>3</tool_uses><duration_ms>45792</duration_ms></usage>
</task-notification>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ cat >> .superpowers/sdd/00-overview/progress.md <<'EOF' ⏎ Task 4.5: fix round 1/5 (3 addressed, 0 open; commits 2ef7c28..77ac110) ⏎ Task 4.5: complete (commits
… [1,528 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
ok
```

</details>

- 🔧 **Agent** · `prompt=You are implementing Task 4.6: Frontend — my assignments. ⏎  ⏎ This is task 27 of 33 in the build of "Mission Control", a multi-tenant Django+DRF / React SPA product, and the **last task of Stage 4**. The backend
… [7,855 more chars — see the .jsonl]`

<details><summary>⤷ Agent result</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: a9927b22328cb81b4 (internal ID - do not mention to user. Use SendMessage with to: 'a9927b22328cb81b4', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do
… [580 more chars — see the .jsonl]
```

</details>

### 🤖 Assistant — 2026-08-12 05:42

**Task 4.5 done** (`77ac110`, review clean) — 26/33. Task 4.6 (my-assignments) is running; it's the last task of Stage 4, and much of its API layer already exists from 4.5, so it's mostly wiring UI onto tested hooks.

## 🧑 User — 2026-08-12 05:46

<task-notification>
<task-id>a9927b22328cb81b4</task-id>
<tool-use-id>toolu_011LHvyqXAyZ8WxGNtaHVKVe</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/a9927b22328cb81b4.output</output-file>
<status>completed</status>
<summary>Agent "Implement Task 4.6: my assignments UI" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>**Status:** DONE
- Commit: `e7116ce` feat: my-assignments page with accept/decline flows
- Test summary: 66/66 frontend tests pass (6 new for my-assignments), `npm run build` passes clean
- No concerns — pre-existing API-layer symbols (`MyAssignmentSchema`, `useMyAssignments`, `useRespondAssignment`) were used unchanged, verified correct against the contract
- One note: task prompt's file path for the API layer was slightly off (`features/assignments/api/assignments.ts`, not `features/missions/api/assignments.ts`) — no code impact, just found it during research
- Report: `/Users/samrichards/code/mission-control-mutinex/.superpowers/sdd/00-overview/task-4.6-report.md`</result>
<usage><subagent_tokens>95471</subagent_tokens><tool_uses>45</tool_uses><duration_ms>279621</duration_ms></usage>
</task-notification>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ OUT=.superpowers/sdd/00-overview/review-77ac110..e7116ce.diff ⏎ { ⏎   echo "# Review package: 77ac110..e7116ce" ⏎   echo; echo "## Commits"; git log --oneline
… [216 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
24695 .superpowers/sdd/00-overview/review-77ac110..e7116ce.diff
```

</details>

- 🔧 **Agent** · `prompt=You are reviewing one task's implementation: first whether it matches its requirements, then whether it is well-built. This is a task-scoped gate, not a merge review — a broad whole-branch review happens separatel
… [7,477 more chars — see the .jsonl]`

<details><summary>⤷ Agent result</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: ac3e57ff9a84ff530 (internal ID - do not mention to user. Use SendMessage with to: 'ac3e57ff9a84ff530', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do
… [580 more chars — see the .jsonl]
```

</details>

### 🤖 Assistant — 2026-08-12 05:47

Task 4.6 committed (`e7116ce`, 66 frontend tests, build clean). Review running — its central claim is that the pre-existing API hooks were correct unchanged, so I've asked the reviewer to verify that rather than accept it.

## 🧑 User — 2026-08-12 05:49

<task-notification>
<task-id>ac3e57ff9a84ff530</task-id>
<tool-use-id>toolu_01DesvFkXyYB9j62hSeeAx4z</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/ac3e57ff9a84ff530.output</output-file>
<status>completed</status>
<summary>Agent "Review Task 4.6 (spec + quality)" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>### Spec Compliance

✅ Spec compliant

Verified against the live backend contract (`backend/mission_control/missions/apis/assignments.py:76-99,140-154`):
- `MyAssignmentSchema` (`frontend/src/features/assignments/api/assignments.ts:114-121`) matches `AssignmentOutputSerializer` exactly: `id`, `status` (enum), `decline_reason` (non-nullable string — backend model is `TextField(blank=True)`, model.py:95, so `""` not `null`, correctly non-nullable in the zod schema), `responded_at` (`z.string().nullable()` — matches `DateTimeField(allow_null=True)`), nested `mission` object with `id/name/status/start_date/end_date/description`.
- `useMyAssignments` (assignments.ts:125-135) parses `PaginatedSchema(MyAssignmentSchema)` and takes `.results` — correctly consumes the standard paginated envelope per the plan-wide ruling, not a bare array.
- `useRespondAssignment` (assignments.ts:137-154) invalidates `MY_ASSIGNMENTS_KEY = ["me","assignments"]` on success — the same key the list query uses — so the list refetches after any respond.
- Body shape `reason ? {action, reason} : {action}` matches the backend's optional `reason` field (`InputSerializer`, `required=False, allow_blank=True, default=""`).

The implementer's central claim — that the pre-existing API layer was correct and needed no changes — is verified true.

Route gating: `router.tsx:52-59` wraps `MyAssignmentsPage` in `&lt;RequirePermission permission="assignment.respond"&gt;`, using the shared `hasPermission`/`RequirePermission` from `lib/auth.tsx`, consistent with every other gated route in the file (no ad-hoc role check). Checked `directorUser` fixture (`testing/mocks.ts:14-22`) — no `assignment.respond` in its permission list, so `RequirePermission` redirects a director to `/` (`lib/auth.tsx:31-34`), which resolves via `HomeRedirect` to the dashboard placeholder — sensible, not a dead end. Nav item at `components/layout/app-layout.tsx:8` is already gated on the same permission (pre-existing, outside this diff).

Group logic:
- Pending = `status === "proposed"` only (`my-assignments-page.tsx:140`) — Accept/Decline buttons render *exclusively* inside this group (lines 188-217), so an accepted/declined/removed row, or one on a terminal mission, can never surface the buttons that would trigger a guaranteed 400.
- Upcoming = `accepted` and mission not `completed`/`cancelled` (lines 105-107), matching the brief verbatim.
- History = everything else (line 142), muted styling + status badge, decline reason shown for declined rows.
- Decline reason is genuinely optional: input starts empty, Decline button is never disabled on empty text (line 288 only disables on in-flight, unlike `transition-buttons.tsx`'s required-reason button at transition-buttons.tsx:110), and `declineReason.trim() || undefined` (line 167) omits the key entirely — verified by test 3 asserting `posted` has no `reason` key.
- 400s surface the server's real `message` via `errorMessage(err)` (lines 149, 172), not a generic string — `errorMessage()` (`api-errors.ts:27-43`) already returns the raw message for business-rule 400s (only substitutes for the generic `"Validation error"` case). Verified by test 4, which asserts the exact server string appears and the card stays in Pending.

No Stage 5 (matcher dialog) or Stage 6 (dashboard) content present — diff is scoped to exactly the four files listed in the brief/report.

⚠️ Cannot verify from diff: the report's manual-smoke checklist (lead proposes → crew accepts → lead sees coverage fill → approve; decline reason visible to lead in roster popover) requires the real dev-compose stack; not verifiable from static diff review. Not blocking — this is standard end-to-end smoke, and the roster-popover display of decline reason belongs to Task 4.5's staffing panel, not this diff.

### Strengths

- Correct, minimal reuse of the pre-existing API layer — no unnecessary churn, and the report's "verified unchanged" claim holds up against the actual backend serializer.
- Query branch order `isLoading → isError → data` followed precisely (`my-assignments-page.tsx:129-138`), with `role="alert"` on the error paragraph — matches the mandatory pattern and is directly tested (test 6).
- Accept/Decline buttons are structurally impossible to reach from a non-`proposed` row (rendered only inside the `pending.map` block), which is the strongest possible defense against the named 400-bait risk.
- Per-card `respondingId` prevents one in-flight mutation from disabling every other card's buttons — correct UX for a shared mutation object.
- Tests use Testing Library roles/labels against real MSW requests (`getByRole`, `getByLabelText`, `within(section)`), not implementation details, and directly assert the exact POST body for all three respond variants (accept, decline+reason, decline-no-reason) plus the 400 message text.
- Single MSW instance, `resetMockData()` reseeds `myAssignments`, `onUnhandledRequest: "error"` preserved (`testing/setup.ts:22`, `mocks.ts:180-187`).

### Issues

#### Critical (Must Fix)
None.

#### Important (Should Fix)
None.

#### Minor (Nice to Have)
- `my-assignments-page.tsx:271-295` — the decline dialog has no explicit "Cancel" button in the footer, only the `Dialog`'s default `X`/Escape close. This matches the pre-existing `transition-buttons.tsx` pattern exactly (also no footer Cancel), so it's not a new deviation, but an explicit Cancel button would be marginally clearer UX.
- Test coverage clusters on `declined` and `accepted-on-completed` for History; a `removed` assignment (present in the status enum and in `ASSIGNMENT_STATUS_LABELS`, `my-assignments-page.tsx:98`) is never exercised by a test. Low risk since the grouping logic (`status !== "proposed" &amp;&amp; !isUpcoming`) trivially covers it, but it's an easy gap to close.
- `MissionDates` (my-assignments-page.tsx:109-115) renders raw ISO date strings (`2026-09-01 – 2026-09-30`) unformatted; cosmetic only, brief just asked for "dates."

### Assessment
**Task quality:** Approved
**Reasoning:** The implementation matches the brief and every named risk (proposed-only respond buttons, optional decline reason, real 400 messages, refresh-on-response, permission-gated routing) is correctly handled and largely test-covered; the pre-existing API layer's correctness was independently re-verified against the backend serializer/selector and matches the contract exactly. No scope creep, no critical or important defects found.</result>
<usage><subagent_tokens>63359</subagent_tokens><tool_uses>22</tool_uses><duration_ms>122596</duration_ms></usage>
</task-notification>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex/backend && uv run pytest 2>&1 | tail -2 && uv run ruff check . 2>&1 | tail -2 ⏎ cd ../frontend && npm test -- --run 2>&1 | grep -E 'Test Files|Tests ' && npm run
… [48 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
.......................                                                  [100%]
311 passed in 63.11s (0:01:03)
All checks passed!
 Test Files  9 passed (9)
      Tests  66 passed (66)
✓ built in 1.52s
```

</details>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ docker compose -f docker-compose.dev.yml up -d backend >/dev/null 2>&1 ⏎ for i in $(seq 1 40); do curl -s -o /dev/null http://localhost:8000/api/v1/skills/ 2>/
… [2,518 more chars — see the .jsonl]`

<details><summary>⤷ Bash result ⚠️ error</summary>

```
Exit code 1
=== APPROVE with NOBODY staffed -> must be blocked by the staffing guard ===
status=400 {"message":"Mission staffing is not valid.","extra":{"errors":["Requirement Orbital Welding ≥5 needs 1, has 0.","Mission needs at least 1 accepted crew (min_crew); has 0."]}}
=== propose crew 6, crew ACCEPTS ===
assignment=
{'accepted_count': 0, 'fully_covered': False}
=== APPROVE now -> should succeed ===
Traceback (most recent call last):
  File "<string>", line 1, in <module>
    import sys,jso
… [123 more chars — see the .jsonl]
```

</details>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ tok(){ curl -s -X POST http://localhost:8000/api/v1/auth/token/ -H 'Content-Type: application/json' -d "{\"email\":\"$1\",\"password\":\"orbit-demo-2026\"}" |
… [742 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
mission=4
=== crew list ===
{
    "results": [
        {
            "id": 6,
            "name": "Crew1 Meridian",
            "email": "crew1@meridian-orbital.test",
            "skills": [
                {
                    "skill_id": 1,
                    "name": "Orbital Welding",
                    "proficiency": 7
                }
            ]
        }
    ],
    "count": 1,
    "limit": 25,
    "offset": 0
}
=== propose raw response ===
status=400
{"message":"Validation error","
… [59 more chars — see the .jsonl]
```

</details>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ echo "=== brief 4.3 propose body ==="; grep -n "user_ids\|user_id" .superpowers/sdd/00-overview/task-4.3-brief.md | head -8 ⏎ echo "=== frontend propose call =
… [101 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
=== brief 4.3 propose body ===
9:  - `assignments_propose(*, actor, mission, user_ids: list[int]) -> list[Assignment]` — ownership rule (lead owns / director); mission non-terminal; users must be active CREW_MEMBERs of the tenant, not already live-assigned to this mission, **not hard-blocked** for the mission range (`ApplicationError` naming them); live count + new ≤ `max_crew`
14:  - `GET /api/v1/missions/<id>/staffing/` (perm `mission.view`) → `{requirements: [...], accepted_count, min_crew, m
… [1,252 more chars — see the .jsonl]
```

</details>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ tok(){ curl -s -X POST http://localhost:8000/api/v1/auth/token/ -H 'Content-Type: application/json' -d "{\"email\":\"$1\",\"password\":\"orbit-demo-2026\"}" |
… [2,989 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
=== bulk propose crew 6 ===
assignment=1
=== still not approvable: proposed != accepted ===
status=400 {"message":"Mission staffing is not valid.","extra":{"errors":["Requirement Orbital Welding ≥5 needs 1, has 0.","Mission needs at least 1 accepted crew (min_crew); has 0."]}}
=== crew accepts ===
{'accepted_count': 1, 'fully_covered': True}
=== approve now ===
approved
=== a SECOND mission over the same dates: is crew 6 now hard-blocked? ===
status=400 {"message":"Unavailable for these dates: C
… [368 more chars — see the .jsonl]
```

</details>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ cat >> .superpowers/sdd/00-overview/progress.md <<'EOF' ⏎ Task 4.6: complete (commits 77ac110..e7116ce, review clean, spec OK) - no fix round needed ⏎   - Revi
… [2,370 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
ok
```

</details>

- 🔧 **Agent** · `prompt=You are implementing Task 5.1: Matching engine. ⏎  ⏎ This is task 28 of 33 in the build of "Mission Control", a multi-tenant Django+DRF / React SPA product, and the first task of Stage 5. Stages 1-4 are complete:
… [9,154 more chars — see the .jsonl]`

<details><summary>⤷ Agent result</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: ac58fb122070c0b55 (internal ID - do not mention to user. Use SendMessage with to: 'ac58fb122070c0b55', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do
… [580 more chars — see the .jsonl]
```

</details>

### 🤖 Assistant — 2026-08-12 05:53

## Stage 4 complete — 27/33 tasks

**Backend 311 tests + ruff clean, frontend 66 tests, build clean.** The live gate is the most satisfying one yet — the whole staffing domain works end to end in the real stack:

| Step | Result |
|---|---|
| Approve with nobody staffed | `400` — *"Requirement Orbital Welding ≥5 needs 1, has 0"* + min_crew error |
| Approve with crew only **proposed** | still `400` — proposed ≠ accepted, the rule holds |
| Crew accepts → staffing | `accepted_count: 1, fully_covered: true` |
| Approve | `approved` |
| Propose same person to an **overlapping** mission | `400 "Unavailable for these dates: Crew1 Meridian."` |
| Cancel the approved mission | crew's row flips to `removed` |
| Re-propose the freed person | `201` — block released |

That's the availability rule, the approve guard, and the cancel cascade all confirmed against real Postgres rather than just unit tests.

Stage 5 has begun with Task 5.1, the matching engine — the longest brief in the plan at 371 lines — running on the stronger model.

## 🧑 User — 2026-08-12 06:19

<task-notification>
<task-id>ac58fb122070c0b55</task-id>
<tool-use-id>toolu_01YCXmh1RafrMXwDRcDpQomD</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/ac58fb122070c0b55.output</output-file>
<status>completed</status>
<summary>Agent "Implement Task 5.1: matching engine" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>- **Status:** DONE
- **Commit:** `f4e1d88` feat: greedy set-cover matching engine with explanations and diagnoses
- **Tests:** 344 passed (311 before + 30 new matching tests + 3 for the new staffing selector), zero warnings; `ruff check .` clean; 9 queries asserted at two roster sizes; verified live against dev Postgres (rich 40-crew scenario inside a rolled-back transaction — dev data untouched).
- **Concerns:**
  - Five documented divergences from the brief's *sample code* (its Interfaces contract is implemented exactly). The load-bearing ones: (1) workload now calls a new `staffing.committed_assignments()` selector instead of re-writing `mission__start_date__lte`/`end_date__gte`/`HARD_BLOCK_MISSION_STATUSES` inside `matching.py` — the Global Constraint's single-source rule governs per the STANDING RULE; (2) `all qualified crew unavailable` is judged against the hard blocks rather than the leftover pool (the snippet would report a person it had just seated as "unavailable"); (3) bench candidates are scored *for the seat they're an alternative for*, replacing a hidden `−proficiency/100` sort term that made every displayed score identical.
  - Wording gap, not a defect: when the roster is simply too shallow (one qualified person, two seats), the brief's closed three-reason list forces the catch-all `max_crew too small`. Flagged for Task 5.3's copy or a possible fourth reason.
- **Report:** `/Users/samrichards/code/mission-control-mutinex/.superpowers/sdd/00-overview/task-5.1-report.md`</result>
<usage><subagent_tokens>115052</subagent_tokens><tool_uses>48</tool_uses><duration_ms>1540491</duration_ms></usage>
</task-notification>

- 🔧 **Bash** · `command="/Users/samrichards/.claude/plugins/cache/claude-plugins-official/superpowers/6.2.0/skills/subagent-driven-development/scripts/review-package" /Users/samrichards/code/mission-control-mutinex/docs/superpowers/plan
… [59 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
wrote /Users/samrichards/code/mission-control-mutinex/.superpowers/sdd/00-overview/review-e7116ce..f4e1d88.diff: 1 commit(s), 43102 bytes
```

</details>

- 🔧 **Agent** · `prompt=You are reviewing one task's implementation: first whether it matches its requirements, then whether it is well-built. This is a task-scoped gate, not a merge review — a broad whole-branch review happens separatel
… [7,855 more chars — see the .jsonl]`

<details><summary>⤷ Agent result</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: a2af7fb6c9984c789 (internal ID - do not mention to user. Use SendMessage with to: 'a2af7fb6c9984c789', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do
… [580 more chars — see the .jsonl]
```

</details>

### 🤖 Assistant — 2026-08-12 06:20

Task 5.1 committed (`f4e1d88`) — **backend 311 → 344 tests**, query count asserted at *two* roster sizes (one size proves nothing about constancy), and the availability rule consumed through a new selector rather than re-derived inside the matcher.

It reported five divergences from the brief's sample code, three of them load-bearing. Reviewing on the stronger model with instructions to walk the scoring formula term by term and rule on each divergence.

## 🧑 User — 2026-08-12 06:25

<task-notification>
<task-id>a2af7fb6c9984c789</task-id>
<tool-use-id>toolu_017eW6GCXUBS1D7Su57L5ibU</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/a2af7fb6c9984c789.output</output-file>
<status>completed</status>
<summary>Agent "Review Task 5.1 (spec + quality)" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>### Spec Compliance

- ✅ **Spec compliant** on the brief's Interfaces contract. Verified term by term:
  - Constants `W_PROFICIENCY=1.0`, `W_WORKLOAD=0.5`, `W_SOFT_CONFLICT=0.75`, `WORKLOAD_WINDOW_DAYS=90` — `matching.py:44-47`.
  - Dataclass field names/orders match the brief exactly (`matching.py:60-98`); `breakdown` keys are exactly the three specified (`matching.py:232-236`).
  - Score: `matching.py:230` is `W_PROFICIENCY * mean_fit + W_WORKLOAD * balance - W_SOFT_CONFLICT * penalty`, with `mean_fit` = mean of `_proficiency_fit` over the seats actually being covered (`matching.py:103-105`, `(prof − min_prof)/9`), `balance = 1 - min(workload/90, 1)` (`matching.py:228`), `penalty = 1.0 if conflicts.get(uid) else 0.0` (`matching.py:229`). Every component, every weight, matches brief §3. No hidden term. Rounding is presentation-only — ranking uses the unrounded score (`matching.py:274`, `287`, `330`).
  - Steps 1–6 of the algorithm all present: open seats from `mission_coverage` (`matching.py:139-152`), pool construction (`matching.py:155-175`), greedy with "at most one seat per skill, the most demanding" (`matching.py:203-222`, `264-281`), top-up to `min_crew` (`matching.py:285-294`), diagnosis (`matching.py:298-317`), alternatives (`matching.py:319-349`).
- ✅ **Availability rule never restated.** `grep -nE "start_date__lte|end_date__gte|MissionStatus|objects_unscoped|APPROVED|ACTIVE" matching.py` returns nothing. Every date/status predicate is a call into `selectors/staffing.py`. `committed_assignments` (`staffing.py:85-104`) is a projection change over the existing `_hard_block_qs` (`staffing.py:57-67`), not a second expression of the rule.
- ✅ **Scope clean.** Four files touched: the engine, the one new selector, and their tests. No API, no serializer, no URL, no frontend.
- ✅ **Tenant scoping.** `User.objects.filter(tenant_id=require_current_tenant_id(), ...)` at `matching.py:169-173` with a comment explaining it is mandatory (the `User`-is-not-`TenantModel` interface fact). No `objects_unscoped` anywhere in application code.
- ⚠️ **Cannot verify from diff:** the reported 344-passing full-suite run and the three mutation checks. The code supports the 9-query claim (see Strengths) and the two-roster-size assertion is present in the diff at `test_matching.py:442-459`.

### Rulings on the five reported divergences

1. **New `staffing.committed_assignments()` selector — correct call.** The brief's sample (brief:220-231) would have written `mission__status__in=HARD_BLOCK_MISSION_STATUSES, mission__start_date__lte=…, mission__end_date__gte=…` inside `matching.py`; that is exactly the restatement the STANDING RULE forbids, so the constraint governs and the sample is the finding. Placement is right (a read, in `selectors/`), shape is right (returns a `QuerySet[Assignment]` with `select_related("mission")`, `staffing.py:104`), and it duplicates nothing — it and `hard_blocked_user_ids` both delegate to `_hard_block_qs`, differing only in projection. Approved.
2. **"All qualified crew unavailable" judged against hard blocks — correct, and their reasoning checks out.** The sample's `qualified_available = any(… for uid in pool)` (brief:333-335) reads a pool from which `pool.pop(uid)` has already removed seated members (brief:300), so one qualified person + two same-skill seats yields "all qualified crew unavailable" about someone the sample just seated. The implementation's `qualified &lt;= blocked_ids` (`matching.py:307`) matches the brief's *prose* ("qualified people exist but all were **hard-blocked**", brief:20). Approved — this is a bug fix, not a divergence.
3. **Bench candidates scored for their seat — faithful and an improvement.** The sample's `scored(uid, [])` (brief:348) forces `mean_fit = 0`, so every displayed score under a requirement is identical, while the actual order comes from the undisclosed `- prof/100` term in the sort key (brief:349) — which the brief's own Interfaces line ("ranked by score", brief:12) contradicts. Scoring against the single seat (`matching.py:327-329`) makes the displayed number the thing that produced the order. Approved; see Minor 1 for the missing test.
4. **`capacity = max(max_crew − live, 0)`** (`matching.py:160`) — correct; the sample emits a negative `open_capacity` for an over-staffed mission.
5. **Structural tidying** — no behaviour change, and the `_OpenSeat` dataclass plus the single `min`-by-key pass (`matching.py:266-278`) are strictly clearer than sorting tuples that carry dicts. One overclaim in the report: the sample's `candidates.sort(reverse=True)` could never `TypeError`, because the unique `-uid` at index 2 always resolves the comparison before reaching the dict. Harmless, but it is a reminder the report is not self-verifying.

### Strengths

- **Determinism is genuinely total, not just claimed.** Greedy key `(-len(seats), -score, user_id)` (`matching.py:274`); top-up `(-score, uid)` (`matching.py:287`); bench `(-score, user_id, …)` (`matching.py:330`); seat-within-skill `(min_proficiency, -requirement_id)` (`matching.py:215-219`); a candidate's `seats` sorted by `skill_id` (`matching.py:222`); roster `order_by("id")` (`matching.py:172`). Named check on the one ordering the module does not own: `mission_coverage` orders `("skill__name", "-min_proficiency", "id")` (`staffing.py:200-202`), so the `unfilled_seats` and `alternatives` sequences inherit a total order. Nothing depends on unordered DB output.
- **Query count verified by reading, and the 9 add up.** `mission_coverage` = 3 (`staffing.py:199-215`), live assignments (`matching.py:155`), `hard_blocked_user_ids` (`matching.py:162`), roster (`matching.py:169`), proficiencies (`matching.py:180`), `committed_assignments` (`matching.py:124`), `soft_conflicts_for_users` — one query, subquery inlined via `.values("id")` (`staffing.py:123-136`). The greedy, top-up, diagnosis and alternatives loops read only from dicts built above; `pool.pop` and `user.name` touch loaded instances. The two-roster-size assertion (`test_matching.py:442-459`) is the right way to prove constancy.
- **Weights are pinned by literals, not by the constants they test.** `test_matching.py:151-157` pins all four to literal values; `test_matching.py:170` asserts `round(1.0 * (3/9) + 0.5 * 1.0, 3)` and `test_matching.py:201` asserts `… − 0.75 * 1.0` — both written with literals, so changing any weight in the module breaks them.
- **Hard-blocked vs soft-conflicted are structurally distinct:** hard blocks removed from the pool (`matching.py:174-175`) so they cannot be proposed *or* benched; soft conflicts stay, take `−0.75`, and the conflicting missions are attached verbatim. Pinned by `test_matching.py:213-226` and `:192-210`.
- **`soft_conflicts_for_users` is read only through `.get(uid, [])`** (`matching.py:229`, `:318` equivalent in `take`), honouring the omit-empty contract.
- **Degenerate cases are all covered:** no requirements (`test_matching.py:308`), empty roster (`:320`), skill-less crew (`:309-311`), nobody qualified (`:174`), `required_count&gt;1` (`:344`, `:170`), multi-requirement candidate (`:75`, `:256`), inactive/non-crew (`:328`), cross-tenant (`:340`).

### Issues

#### Critical (Must Fix)
None.

#### Important (Should Fix)

**1. Deactivated crew with a live assignment still consume `max_crew` capacity and count toward `min_crew`** — `matching.py:155-160`.

```python
live_user_ids = set(
    Assignment.objects.filter(mission=mission, status__in=LIVE_ASSIGNMENT_STATUSES)...
)
capacity = max(mission.max_crew - len(live_user_ids), 0)
```

This counts assignments itself rather than through the staffing selectors, and so ignores `is_active`. The binding human ruling in `constraints.md:131-136` ("Deactivated crew do not fill staffing seats… both must read the staffing selectors rather than counting assignments themselves") and `_accepted_assignments_qs`'s own docstring (`staffing.py:154-156`: deactivated members "stop filling seats and stop counting toward `min_crew`/`max_crew`") say the opposite. `staffing_validation_errors` compares `report.accepted_count` — active-only — against `min_crew`/`max_crew` (`staffing.py:310-319`).

Consequence, in a reachable state (deactivate a crew member who is live on a mission, then run the matcher): the matcher believes a seat is taken by someone who can never accept, under-proposes against `max_crew`, stops the `min_crew` top-up early (`matching.py:285`), and therefore returns a team the approve guard will reject as short of `min_crew` — with no diagnosis saying why. `open_capacity` is also reported too low.

Plan-mandated in origin (the brief's sample does the same, brief:245-247), but it contradicts a later binding ruling, so the ruling governs. Fix: add `user__is_active=True` to the live-assignment filter. Safe — such a user is already out of `roster`/`pool` via the `is_active` filter at `matching.py:171`, so they cannot be re-proposed.

**2. `"max_crew too small"` is emitted while the same result reports spare capacity** — `matching.py:310`, pinned by `test_matching.py:256-266`.

In that test `max_crew=4`, one member is seated, so `open_capacity == 3` — yet the unfilled seat's reason is `"max_crew too small"`. The `MatchResult` contradicts itself, and Task 5.3 is about to render both fields on the same panel. This is the wording gap the implementer flagged; it is real, and it is worse than "imprecise" because the two fields disagree inside one payload.

This is plan-mandated (the brief closes the reason list at three, brief:11/20), so it needs a controller decision rather than a unilateral fix — but it should be decided **before** 5.3 writes copy, because adding a fourth reason afterwards changes a string 5.3 will have branched on. Two acceptable resolutions: (a) add `"not enough qualified crew"` for the case `qualified ⊄ blocked_ids and capacity &gt; 0`, keeping `"max_crew too small"` for `capacity == 0`; or (b) keep three reasons and rename the catch-all to something honest like `"no more crew available"`. Option (a) is the two-line change the implementer describes and is the one I'd recommend.

#### Minor (Nice to Have)

**1. Divergence 3's whole point is untested** — `test_matching.py:350-359`. `test_alternatives_are_ranked_by_score_descending` asserts ids, proficiencies and sortedness, but never a numeric `score`. In that fixture the crew are created in descending proficiency, so their ids ascend in the same order — meaning a regression back to `score_for(uid, [])` (all bench scores equal, order falling through to the ascending-`user_id` tie-break) produces the identical id list, the identical proficiency list, and a trivially-sorted equal-score sequence. Every assertion still passes. Add one exact-value assertion, e.g. that the top bench candidate's `score == round(1.0 * (3/9) + 0.5, 3)` and that two candidates with equal proficiency but different workload get different scores.

**2. `committed_assignments` returns an unordered QuerySet** — `staffing.py:104`. Harmless for the only caller (`_committed_days` sums into a dict, `matching.py:124-129`), but a public selector whose row order is DB-dependent is a trap for the next caller. Add `.order_by("mission__start_date", "id")`.

**3. `match_mission` is a pure read living in `services/`** — `matching.py`. HackSoft convention (`constraints.md:6`) puts reads in `selectors`. Plan-mandated: the brief's Files section names `services/matching.py` and Task 5.2's brief will import `missions.services.matching`. Recording it only so it is not re-litigated per task — **do not move it**, interface stability across 5.2/5.3 is worth more than the convention here.

### Assessment

**Task quality:** Needs fixes

**Reasoning:** The engine is correct where it matters most — the scoring formula matches the brief term for term, every ordering is total, the availability rule is single-sourced (grep-clean), and the 9-query claim holds under code reading — and all five reported divergences from the sample are correct calls, three of them fixing real defects in the sample. Two things block a clean pass: the live-assignment count ignores `is_active`, contradicting a binding ruling and producing un-approvable teams for deactivated-crew missions; and the `"max_crew too small"` diagnosis contradicts `open_capacity` in the same payload, which needs a controller ruling before Task 5.3 writes copy against it.</result>
<usage><subagent_tokens>85304</subagent_tokens><tool_uses>17</tool_uses><duration_ms>331322</duration_ms></usage>
</task-notification>

### 🤖 Assistant — 2026-08-12 06:25

Task 5.1's review found one issue that needs your ruling before Task 5.3 writes UI copy against it.

- 🔧 **AskUserQuestion** · `{"questions": [{"question": "The matcher's diagnosis has a closed list of three reasons per the plan. When the roster is simply too shallow — one qualified person, two seats — it falls through to the catch-all `\"max_cre
… [1,106 more chars — see the .jsonl]`

<details><summary>⤷ AskUserQuestion result</summary>

```
Your questions have been answered: "The matcher's diagnosis has a closed list of three reasons per the plan. When the roster is simply too shallow — one qualified person, two seats — it falls through to the catch-all `"max_crew too small"`, even while the same payload reports `open_capacity: 3`. So the result contradicts itself, and Task 5.3 is about to render both fields on the same panel. How should I resolve it?"="Add a fourth reason (Recommended)". You can now continue with these answers in
… [5 more chars — see the .jsonl]
```

</details>

- 🔧 **SendMessage** · `{"to": "ac58fb122070c0b55", "summary": "Task 5.1 fix round 1: is_active + fourth reason", "message": "Task 5.1 review came back with two Important findings. Fix both plus two small items, re-run the tests covering the am
… [4,736 more chars — see the .jsonl]`

<details><summary>⤷ SendMessage result</summary>

```
{"success":true,"message":"Agent \"ac58fb122070c0b55\" had no active task; resumed from transcript in the background with your message. You'll be notified when it finishes. Output: /private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/ac58fb122070c0b55.output","resumedAgentId":"ac58fb122070c0b55","pin":{"id":"ac58fb122070c0b55","name":"ac58fb122070c0b55","ref":"a7a5b9"}}
```

</details>

### 🤖 Assistant — 2026-08-12 06:31

All five of the implementer's deviations from the brief's sample code were upheld — and three were reclassified as *fixing real defects in the sample*, including one where the sample would have reported a crew member as "unavailable" immediately after seating them.

Two things are being fixed. The matcher counted live assignments directly instead of through the staffing selectors, so it ignored your deactivated-crew ruling — meaning it would return a team the approve guard then rejects, with no explanation. And your fourth-reason ruling is going in now, before Task 5.3 branches on those strings.

## 🧑 User — 2026-08-12 06:43

<task-notification>
<task-id>ac58fb122070c0b55</task-id>
<tool-use-id>toolu_01WLJCRhwiS5jjTnaAv4bJPJ</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/ac58fb122070c0b55.output</output-file>
<status>completed</status>
<summary>Agent "Implement Task 5.1: matching engine" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>- **Status:** DONE
- **Commit:** `2dd7096` fix: deactivated crew free their seat; split the max_crew diagnosis
- **Tests:** 352 passed (344 → +7 matching, +1 staffing), zero warnings; `ruff check .` clean; both fixes mutation-checked and live-verified against dev Postgres in a rolled-back transaction (dev data untouched).

**For Task 5.3 — the closed list of `UnfilledSeat.reason` is now four**, exported as constants from `missions.services.matching`, evaluated in this order:
1. `NO_QUALIFIED_CREW` = `"no qualified crew"` — nobody on the roster meets `min_proficiency`.
2. `ALL_QUALIFIED_UNAVAILABLE` = `"all qualified crew unavailable"` — qualified crew exist, all hard-blocked.
3. `MAX_CREW_TOO_SMALL` = `"max_crew too small"` — **only** when `open_capacity == 0`.
4. `NOT_ENOUGH_QUALIFIED_CREW` = `"not enough qualified crew"` — room exists, nobody blocked, roster too thin.

Invariant 5.3 can rely on: `MAX_CREW_TOO_SMALL` appears **iff** `open_capacity == 0`.

- **Concerns:** one judgement call flagged in the report — I applied `user__is_active=True` at the call site as instructed rather than adding another public staffing selector, so `matching.py` still counts live assignments itself (with the now-correct predicate). Noted the TypeError overclaim and corrected section 10 in place.
- **Report:** `/Users/samrichards/code/mission-control-mutinex/.superpowers/sdd/00-overview/task-5.1-report.md`</result>
<usage><subagent_tokens>137085</subagent_tokens><tool_uses>15</tool_uses><duration_ms>694324</duration_ms></usage>
</task-notification>

- 🔧 **Bash** · `command="/Users/samrichards/.claude/plugins/cache/claude-plugins-official/superpowers/6.2.0/skills/subagent-driven-development/scripts/review-package" /Users/samrichards/code/mission-control-mutinex/docs/superpowers/plan
… [59 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
wrote /Users/samrichards/code/mission-control-mutinex/.superpowers/sdd/00-overview/review-f4e1d88..2dd7096.diff: 1 commit(s), 23317 bytes
```

</details>

- 🔧 **Agent** · `prompt=You are re-reviewing one task's fix round. A previous review produced findings; an implementer has attempted to fix them. Your job is to verdict each finding and inspect the fix diff — nothing else. ⏎  ⏎ ## The Ta
… [5,842 more chars — see the .jsonl]`

<details><summary>⤷ Agent result</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: a10c440ab2b5533a2 (internal ID - do not mention to user. Use SendMessage with to: 'a10c440ab2b5533a2', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do
… [580 more chars — see the .jsonl]
```

</details>

### 🤖 Assistant — 2026-08-12 06:43

Task 5.1 fixes committed (`2dd7096`, 352 tests), both mutation-checked. The diagnosis now has a documented closed list of four reasons with a stated invariant — `"max_crew too small"` appears **iff** `open_capacity == 0` — which Task 5.3 can branch on safely. Re-review is verifying that invariant actually holds in the code rather than just in the report.

## 🧑 User — 2026-08-12 06:47

<task-notification>
<task-id>a10c440ab2b5533a2</task-id>
<tool-use-id>toolu_012WXgHrNFMTPk9sKavzdLDt</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/a10c440ab2b5533a2.output</output-file>
<status>completed</status>
<summary>Agent "Re-review Task 5.1 fix round 1" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>### Finding Verdicts

- **Important 1 — live-assignment count ignored `is_active`.** ADDRESSED. `backend/mission_control/missions/services/matching.py:173-176` now filters `user__is_active=True` on the live-assignment query, with a comment citing the ruling and the failure mode. Verified it changes no previously-correct behaviour: the added predicate is a no-op for active users (it's already `True`), so a *proposed* assignment held by an active user (`test_active_live_member_still_consumes_capacity`, diff lines 289-302) still consumes capacity exactly as before. The new discriminating test `test_deactivated_live_member_frees_their_seat[proposed/accepted]` (diff lines 262-286) was traced by hand against the pre-fix predicate: since `mission_coverage` already excludes deactivated members' accepted assignments via `_accepted_assignments_qs`'s `user__is_active=True` (staffing.py:171), the seat stays "open" under old code too, but the ghost still occupied a capacity slot, so top-up would stop one member short of `min_crew` — the asserted `["Pilot", "Extra Hands"]` would fail, yielding only `["Pilot"]`. Test is genuinely discriminating.

  **Judgement call ruling (inline query vs. new selector):** justified. The claimed conflict is not with the *availability rule* (the hard-block date/mission-status predicate), which stays centralized in `_hard_block_qs`/`hard_blocked_user_ids`/`committed_assignments` — `matching.py` still contains no `start_date__lte`/`end_date__gte`/literal status set. What's duplicated is a single-clause predicate (`user__is_active=True`) that also appears in `_accepted_assignments_qs` (staffing.py:171). No selector currently returns "live" (proposed+accepted) assignment user ids for a mission — `_accepted_assignments_qs` is accepted-only and cannot be reused for capacity, exactly as the implementer argues. Given the predicate is trivial, well-commented, and citing the ruling explicitly, this is acceptable for this round; it is a residual minor duplication risk (a future `live_assignment_user_ids(mission)` selector would fully close it) rather than a defect — logged under Out-of-Scope Observations, not blocking.

- **Important 2 (human ruling) — fourth diagnosis reason.** ADDRESSED, with one overclaim to flag. `matching.py:320-332` implements the four-way branch (`qualified` empty → `NO_QUALIFIED_CREW`; `qualified ⊆ blocked_ids` → `ALL_QUALIFIED_UNAVAILABLE`; `capacity == 0` → `MAX_CREW_TOO_SMALL`; else → `NOT_ENOUGH_QUALIFIED_CREW`). Walked the partition: it is exhaustive and mutually exclusive, no state falls through to the wrong branch. New/updated tests (`test_thin_roster_is_not_reported_as_max_crew_too_small`, `test_one_seat_per_skill_and_the_most_demanding_one`) are discriminating — under the pre-fix 3-branch code both would have emitted `MAX_CREW_TOO_SMALL`, which the assertions now reject. `test_max_crew_too_small_is_only_reported_when_there_is_no_room` correctly pins the positive case. Old string-literal assertions were migrated to the imported constants throughout.

  **The stated invariant is only half true — see New Breakage below.**

- **Minor A — bench score never asserted numerically.** ADDRESSED. `test_alternatives_are_ranked_by_score_descending` (diff lines 405-421) now asserts exact scores `[0.833, 0.722, 0.611]`; traced by hand — under the `score_for(uid, [])` regression every candidate's `mean_fit` becomes 0, producing `0.5, 0.5, 0.5`, which fails the assertion (order alone would have still coincidentally matched due to the id/proficiency correlation, exactly the gap Minor A identified — the new exact-value check closes it). `test_bench_order_follows_score_not_user_id` (diff lines 424-445) adds a case with equal proficiency (7 vs 7) and asymmetric workload where the worse candidate has the *lower* id; traced by hand — its exact-score assertions (`0.722` vs `0.5`) also fail under the `[]`-seats regression (which would give `0.5` vs `0.278`), and the ordering itself is also a genuine id-tie-break trap (`Fresh` must outrank `Busy` despite `busy.id &lt; fresh.id`).

- **Minor B — `committed_assignments` unordered.** ADDRESSED. `staffing.py:104-110` adds `.order_by("mission__start_date", "id")` exactly as specified. `test_committed_assignments_is_ordered_deterministically` (diff lines 475-492) inserts rows out of date order (Third, First, Second) and asserts the returned order is `[First, Second, Third]` — discriminating against the unordered pre-fix query, whose natural row order would follow insertion order.

### New Breakage in the Fix Diff

- **Important (documentation/claim risk for Task 5.3) — the reported invariant "`MAX_CREW_TOO_SMALL` appears iff `open_capacity == 0`" is false in the backward direction.** `matching.py:320-332`. Only the forward direction holds by construction (`MAX_CREW_TOO_SMALL` is gated on `capacity == 0`, so its presence does imply `open_capacity == 0`) — that's the real fix for Finding 2's self-contradiction concern. But `open_capacity == 0` does **not** imply `MAX_CREW_TOO_SMALL` appears anywhere in the result. Concrete counterexample, traced through the code: a mission with `min_crew=2, max_crew=2`, one requirement (some skill, `required_count=1`) that **nobody in the tenant qualifies for**, and two unrelated generalist crew in the pool. The greedy loop covers nothing (nobody qualifies), but the top-up loop (step 5, unconditional on skill) fills both slots with the two generalists to reach `min_crew`, driving `capacity` to `0`. The diagnosis loop then evaluates the still-open seat: `qualified` is empty, so the *first* branch fires (`NO_QUALIFIED_CREW`), never reaching the `capacity == 0` branch. Result: `open_capacity == 0` with `unfilled_seats == [NO_QUALIFIED_CREW]` and no `MAX_CREW_TOO_SMALL` entry at all — directly contradicting the report's stated "iff." No new test in the diff exercises this mixed scenario (top-up consuming capacity while an unrelated seat is unqualified/blocked), so the gap is untested as well as misdescribed. This doesn't corrupt `open_capacity` itself (still reads correctly as 0) or the reason for that seat (`NO_QUALIFIED_CREW` is arguably the more informative label) — but the report explicitly hands Task 5.3 a converse guarantee that does not hold, and 5.3 was flagged as about to rely on it. Recommend correcting the report/docstring to state only the one-directional implication before 5.3 starts.

### Out-of-Scope Observations

- `matching.py`'s live-assignment count still queries `Assignment` directly rather than through a selector (pre-existing design, not introduced this round); the `user__is_active=True` clause added this round is now expressed in two places (`matching.py:175` and `staffing.py:171`). Not a defect given no selector currently serves the "live, not just accepted" shape, but worth a follow-up selector (`live_assignment_user_ids(mission)`) if a third consumer needs the same predicate.
- `match_mission` remaining in `services/` — explicitly out of scope per the brief, not re-litigated.

### Verdict

**Fix round:** All four findings addressed, no new Critical/Important code-behaviour breakage — but the fix report's stated invariant for Task 5.3 ("MAX_CREW_TOO_SMALL iff open_capacity == 0") is overclaimed and should be corrected to the one-directional form before Task 5.3 consumes it, with a test added for the mixed-reason/zero-capacity case shown above.</result>
<usage><subagent_tokens>86558</subagent_tokens><tool_uses>9</tool_uses><duration_ms>221597</duration_ms></usage>
</task-notification>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ grep -nE '^(@dataclass|class |def |W_|NO_QUALIFIED|ALL_QUALIFIED|MAX_CREW|NOT_ENOUGH)' backend/mission_control/missions/services/matching.py | head -30 ⏎ echo
… [98 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
40:W_PROFICIENCY = 1.0
41:W_WORKLOAD = 0.5
42:W_SOFT_CONFLICT = 0.75
61:NO_QUALIFIED_CREW = "no qualified crew"
62:ALL_QUALIFIED_UNAVAILABLE = "all qualified crew unavailable"
63:MAX_CREW_TOO_SMALL = "max_crew too small"
64:NOT_ENOUGH_QUALIFIED_CREW = "not enough qualified crew"
67:@dataclass
68:class ProposedMember:
78:@dataclass
79:class UnfilledSeat:
86:@dataclass
87:class RequirementAlternatives:
94:@dataclass
95:class MatchResult:
102:@dataclass
103:class _OpenSeat:
113:def _proficiency_fit
… [1,549 more chars — see the .jsonl]
```

</details>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ cat >> .superpowers/sdd/00-overview/constraints.md <<'EOF' ⏎  ⏎ ## Matching engine contract (Task 5.1 — binding on Tasks 5.2 and 5.3) ⏎  ⏎ `mission_control.mis
… [3,483 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
ok
```

</details>

- 🔧 **Agent** · `prompt=You are implementing Task 5.2: Match API. ⏎  ⏎ This is task 29 of 33 in the build of "Mission Control", a multi-tenant Django+DRF / React SPA product. Stages 1-4 are complete and verified live. Task 5.1 just lande
… [7,794 more chars — see the .jsonl]`

<details><summary>⤷ Agent result</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: a023fc1ed05de2bcf (internal ID - do not mention to user. Use SendMessage with to: 'a023fc1ed05de2bcf', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do
… [580 more chars — see the .jsonl]
```

</details>

### 🤖 Assistant — 2026-08-12 06:49

**Task 5.1 done** (`2dd7096`, review clean) — 28/33, backend at **352 tests**.

One thing I corrected as controller rather than accepting: the fix report handed Task 5.3 an invariant — *"`max_crew too small` appears **iff** `open_capacity == 0`"* — but the re-reviewer produced a counterexample showing only the forward direction holds. Since 5.3 was about to branch on that guarantee, I've recorded the correct one-directional form in the shared constraints instead.

Task 5.2 (match API) is running.

## 🧑 User — 2026-08-12 06:56

<task-notification>
<task-id>a023fc1ed05de2bcf</task-id>
<tool-use-id>toolu_014swL9hvqgqApWMK9CjH7TG</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/a023fc1ed05de2bcf.output</output-file>
<status>completed</status>
<summary>Agent "Implement Task 5.2: match API" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>**Status:** DONE
Commit: `bb68e4a` feat: match API
Tests: RED (4/5 failed pre-implementation, 404s on missing route) → GREEN (5/5 pass); full suite 357 passed (352 + 5 new), `ruff check .` clean.
No concerns — endpoint is a thin `POST /api/v1/missions/&lt;id&gt;/match/`, gated on `match.run`, 403 for crew, 404 cross-tenant, 400 on terminal mission, response is `dataclasses.asdict(match_mission(mission))` unenveloped (judged not a list endpoint — reasoning in report).
Report: `/Users/samrichards/code/mission-control-mutinex/.superpowers/sdd/00-overview/task-5.2-report.md`</result>
<usage><subagent_tokens>68936</subagent_tokens><tool_uses>36</tool_uses><duration_ms>468166</duration_ms></usage>
</task-notification>

- 🔧 **Bash** · `command="/Users/samrichards/.claude/plugins/cache/claude-plugins-official/superpowers/6.2.0/skills/subagent-driven-development/scripts/review-package" /Users/samrichards/code/mission-control-mutinex/docs/superpowers/plan
… [59 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
wrote /Users/samrichards/code/mission-control-mutinex/.superpowers/sdd/00-overview/review-2dd7096..bb68e4a.diff: 1 commit(s), 7037 bytes
```

</details>

- 🔧 **Agent** · `prompt=You are reviewing one task's implementation: first whether it matches its requirements, then whether it is well-built. This is a task-scoped gate, not a merge review — a broad whole-branch review happens separatel
… [6,910 more chars — see the .jsonl]`

<details><summary>⤷ Agent result</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: ac58ced5a50b2f290 (internal ID - do not mention to user. Use SendMessage with to: 'ac58ced5a50b2f290', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do
… [580 more chars — see the .jsonl]
```

</details>

### 🤖 Assistant — 2026-08-12 06:57

Task 5.2 committed (`bb68e4a`, 357/357). Review running with two judgement calls to rule on — the unenveloped response, and using `dataclasses.asdict` instead of an explicit serializer, which is DRY but means any field later added to a dataclass is automatically exposed over the API with no allowlist.

## 🧑 User — 2026-08-12 06:59

<task-notification>
<task-id>ac58ced5a50b2f290</task-id>
<tool-use-id>toolu_018Proje1yJCu8SnhZVb2DWB</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/ac58ced5a50b2f290.output</output-file>
<status>completed</status>
<summary>Agent "Review Task 5.2 (spec + quality)" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>## Spec Compliance

✅ Spec compliant, with one Important deviation from a Global Constraint (see below).

**Verified against brief (task-5.2-brief.md):**
- `POST /api/v1/missions/&lt;id&gt;/match/`, perm `match.run` — brief explicitly specifies `POST` for this operation (line 8); not a defect, matches the brief on its face.
- `ensure_permission(request.user, Permission.MATCH_RUN)` called before `mission_selectors.mission_get(mission_id)` — `backend/mission_control/missions/apis/matching.py:26-27`. Confirmed `MATCH_RUN = "match.run"` (`users/permissions.py:17`) is granted to `MISSION_LEAD`/`DIRECTOR`, not `CREW_MEMBER` (`users/permissions.py:31-44`), and `mission_get` uses `get_object_or_404` against the tenant-scoped `Mission.objects` manager (`missions/selectors/missions.py:24-28`), so cross-tenant returns 404 not 403 — confirmed by `test_cross_tenant_mission_404` and `test_crew_cannot_run_matcher`.
- Terminal-status guard matches the brief's literal `ApplicationError("Cannot match a completed or cancelled mission.")` exactly — `apis/matching.py:27`.
- View contains no business logic: permission check, fetch, terminal guard, call-and-serialize — four lines, confirmed by reading `apis/matching.py:24-29` in full (not truncated).
- No availability-rule restatement: no date predicate, no `{approved, active}` literal set anywhere in the diff. The only local constant (`TERMINAL`) is the mission's own terminal-status set, unrelated to the hard-block/soft-conflict availability rule.
- Query cost: read `services/matching.py` in full — `dataclasses.asdict` and `Response()` are pure Python transforms over already-fetched dataclass data; `ProposedMember.name` is populated from `user.name` inside `match_mission` (`services/matching.py:265`), so the view adds no per-row lookups. The 9-query budget (`test_matching.py:566-580`, unchanged) is untouched by this diff.
- Every dataclass field reaches JSON via `dataclasses.asdict`, confirmed against `services/matching.py:67-99` field-by-field; `reason` values come from the exported constants (`NO_QUALIFIED_CREW` etc., `services/matching.py:61-64`), never hardcoded in the API layer.
- Scope: diff touches exactly `apis/matching.py` (new), `urls.py` (+2 lines), `test_match_api.py` (new) — no UI, no new bulk-propose endpoint, no dashboard code.

**Judgement call 1 — unenveloped response:** Ruled acceptable. `match_mission` returns one structured object with three differently-shaped arrays (`team`, `unfilled_seats`, `alternatives`) plus a scalar (`open_capacity`) — not a homogeneous row-set to page through, and slicing any one array with `limit`/`offset` would leave the others un-paginated, which is incoherent. This matches existing, unchallenged precedent in the same codebase: `MissionDetailApi` and `MissionStaffingApi`'s `staffing_payload` (`apis/assignments.py:18-70`) are both unenveloped structured objects containing arrays. Ruling 2's plan-wide envelope targets genuine list endpoints (`GET /missions/`, `GET /me/assignments/`); this isn't one.

**Judgement call 2 — `dataclasses.asdict` instead of an explicit inline serializer:** Ruled **not acceptable** — see Important finding below.

### Strengths
- View is a genuinely thin four-line `APIView.post` — permission, fetch, guard, response — with zero scoring/filtering/re-ranking logic, consistent with the "no business logic in the API layer" ruling.
- Permission-before-fetch ordering is correct and tested, cross-tenant 404 is correct and tested (`test_cross_tenant_mission_404`), and a genuine shape-asserting test exists (`test_response_shape_matches_dataclass_field_names`, exact `set()` key-equality rather than subset checks).
- Terminal-status guard uses the brief's literal error message verbatim.
- No availability-rule restatement, no extra queries, no scope creep — diff is minimal and matches the brief's file list exactly.

### Issues

#### Important (Should Fix)
1. **`dataclasses.asdict` bypasses the Global Constraint requiring "serializers defined inline in the API class" (plan-mandated).** `apis/matching.py:29` returns `Response(dataclasses.asdict(match_mission(mission)))` with no serializer at all. `constraints.md` line 6 states the HackSoft convention explicitly: "APIs are DRF `APIView` subclasses with serializers defined **inline** in the API class." Every other API in this codebase — including ones returning structured objects with embedded arrays, the closest precedent to this endpoint — honors that: `MissionDetailSerializer` (`apis/missions.py:26-51`) and `staffing_payload` (`apis/assignments.py:18-70`) both hand-construct the response dict field-by-field, acting as an explicit allowlist over the underlying model/dataclass. This endpoint is the only one in the diff set that serializes by generically dumping an internal object's `__dict__`-equivalent straight onto the wire. Per the STANDING RULE ("when a task brief's sample code contradicts the plan's own Global Constraints, the Global Constraint governs... a brief sample that violates a Global Constraint is a finding, not a licence"), the brief's literal instruction to call `dataclasses.asdict` does not excuse this — the implementer should have built an explicit serializer (or a `match_payload`-style dict-builder mirroring `staffing_payload`) reproducing the same shape, and should have flagged the brief/constraint conflict as a judgement call in the report rather than silently taking the unconstrained path. Practical consequence, directly relevant to Task 5.3: any field later added to `ProposedMember`, `UnfilledSeat`, `RequirementAlternatives`, or `MatchResult` for internal bookkeeping is automatically exposed over the API with zero code change and no serializer acting as a gate, and there is no single place in the API layer where the wire contract is written down for the zod schema to be checked against.
   **Fix:** replace `dataclasses.asdict(...)` with an explicit output serializer or dict-builder function (analogous to `staffing_payload`) that enumerates every field by name.

### Minor (Nice to Have)
1. `apis/matching.py:18-20` redeclares `TERMINAL = frozenset({MissionStatus.COMPLETED, MissionStatus.CANCELLED})` rather than importing it. `services/assignments.py:26` already defines the identical, module-level (not underscore-prefixed, so importable) `TERMINAL`. The report's stated rationale ("it's private to that service file's context") is incorrect — it's a public name. Minor DRY duplication of a two-line constant; low risk since both mission statuses are stable, but an avoidable second source of truth. Fix: `from mission_control.missions.services.assignments import TERMINAL`.
2. `test_response_shape_matches_dataclass_field_names` (`test_match_api.py:134-165`) never exercises a scenario with a populated `unfilled_seats` list, so `UnfilledSeat`'s field set (`requirement_id`, `skill_name`, `min_proficiency`, `reason`) and the fact that `reason` renders as one of the four constant strings (not a stray hardcoded copy) are asserted only by construction (via the uniform `dataclasses.asdict` mechanism, and by Task 5.1's own service-level tests) — not directly by this API test. The self-review's claim that the test "asserts the full key set" is true for `team`/`alternatives`/top-level/`breakdown` but overstates coverage of `unfilled_seats`. Low risk given the shared serialization mechanism, but worth a follow-up case with an actually-unfilled seat.

### Assessment
**Task quality:** Needs fixes
**Reasoning:** The endpoint's routing, permission gating, tenancy isolation, terminal-status guard, and freedom from business logic/query blowup are all correct and tested. However, using `dataclasses.asdict` as the response serializer is a plan-mandated violation of the Global Constraint requiring explicit inline serializers — precisely the codebase convention this task should have followed (as `staffing_payload` and `MissionDetailSerializer` demonstrate for structurally similar endpoints) — and it removes the allowlist protection and written-down wire contract that Task 5.3's zod schemas are about to depend on. This should be fixed before treating the endpoint's response shape as a stable contract for 5.3.</result>
<usage><subagent_tokens>56372</subagent_tokens><tool_uses>14</tool_uses><duration_ms>144593</duration_ms></usage>
</task-notification>

- 🔧 **SendMessage** · `{"to": "a023fc1ed05de2bcf", "summary": "Task 5.2 fix round 1: explicit serializer needed", "message": "Task 5.2 review came back \"Needs fixes\" with one Important finding. Fix it plus the two small items, re-run the tes
… [3,925 more chars — see the .jsonl]`

<details><summary>⤷ SendMessage result</summary>

```
{"success":true,"message":"Agent \"a023fc1ed05de2bcf\" had no active task; resumed from transcript in the background with your message. You'll be notified when it finishes. Output: /private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/a023fc1ed05de2bcf.output","resumedAgentId":"a023fc1ed05de2bcf","pin":{"id":"a023fc1ed05de2bcf","name":"a023fc1ed05de2bcf","ref":"1e0d25"}}
```

</details>

### 🤖 Assistant — 2026-08-12 07:00

Your standing rule did its job here without needing you: the brief told the implementer to serialize with `dataclasses.asdict`, but that contradicts the Global Constraint requiring explicit inline serializers — so the constraint wins and it's being replaced with a hand-enumerated payload.

It's not pedantry in this case. Without a serializer acting as an allowlist, any field later added to those dataclasses for internal bookkeeping would publish itself over the API automatically, and there'd be no written-down wire contract for Task 5.3's zod schemas to be checked against. The shape stays byte-identical, so the existing shape test passing unchanged is the proof.

## 🧑 User — 2026-08-12 07:03

<task-notification>
<task-id>a023fc1ed05de2bcf</task-id>
<tool-use-id>toolu_01VskukTaBvrswQzQcdAd3Ta</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/a023fc1ed05de2bcf.output</output-file>
<status>completed</status>
<summary>Agent "Implement Task 5.2: match API" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>**Status:** DONE
Commit: `ddd3b94` fix: explicit match payload serialization, reuse shared TERMINAL
Tests: focused `test_match_api.py` 6/6 pass; full suite 358 passed, `ruff check .` clean
No concerns — JSON shape verified byte-identical (pre-existing shape test unchanged), `TERMINAL` now imported not redeclared, new test covers `UnfilledSeat` shape and `NO_QUALIFIED_CREW` reason
Report: `/Users/samrichards/code/mission-control-mutinex/.superpowers/sdd/00-overview/task-5.2-report.md` (fix report appended)</result>
<usage><subagent_tokens>79982</subagent_tokens><tool_uses>12</tool_uses><duration_ms>174704</duration_ms></usage>
</task-notification>

- 🔧 **Bash** · `command="/Users/samrichards/.claude/plugins/cache/claude-plugins-official/superpowers/6.2.0/skills/subagent-driven-development/scripts/review-package" /Users/samrichards/code/mission-control-mutinex/docs/superpowers/plan
… [59 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
wrote /Users/samrichards/code/mission-control-mutinex/.superpowers/sdd/00-overview/review-bb68e4a..ddd3b94.diff: 1 commit(s), 6786 bytes
```

</details>

- 🔧 **Agent** · `prompt=You are re-reviewing one task's fix round. A previous review produced findings; an implementer has attempted to fix them. Your job is to verdict each finding and inspect the fix diff — nothing else. This is a smal
… [4,517 more chars — see the .jsonl]`

<details><summary>⤷ Agent result</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: a11f2747c03c1b0d4 (internal ID - do not mention to user. Use SendMessage with to: 'a11f2747c03c1b0d4', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do
… [580 more chars — see the .jsonl]
```

</details>

### 🤖 Assistant — 2026-08-12 07:04

Task 5.2 fix committed (`ddd3b94`, 358/358). Re-review is checking the one real hazard of hand-enumerating a shape — that it silently changes it — by walking every field of all four dataclasses and confirming the pre-existing shape test is untouched.

## 🧑 User — 2026-08-12 07:04

<task-notification>
<task-id>a11f2747c03c1b0d4</task-id>
<tool-use-id>toolu_01RQcqsjtBMRJfjAueR8Pm7H</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/a11f2747c03c1b0d4.output</output-file>
<status>completed</status>
<summary>Agent "Re-review Task 5.2 fix round 1" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>**Important — explicit serialization instead of `dataclasses.asdict`** — ADDRESSED at `apis/matching.py:40-84`. The fix replaces `dataclasses.asdict(match_mission(mission))` with an explicit `match_payload(result: MatchResult) -&gt; dict` function that enumerates all four dataclasses' fields by name: `MatchResult` (team, unfilled_seats, alternatives, open_capacity); `ProposedMember` (user_id, name, seats, score, breakdown, workload_days, soft_conflicts); `UnfilledSeat` (requirement_id, skill_name, min_proficiency, reason); `RequirementAlternatives` (requirement_id, skill_name, min_proficiency, candidates). Nested structures (seats, breakdown, soft_conflicts, candidates) pass through as plain dicts unchanged. The response is now `Response(match_payload(...))` at line 94. Pre-existing test `test_response_shape_matches_dataclass_field_names` remains unchanged in the diff and asserts the full key sets.

**Minor A — `TERMINAL` redeclared** — ADDRESSED at `apis/matching.py:32`. The local `TERMINAL = frozenset(...)` redeclaration (old lines 36–38) is removed; the code now imports `from mission_control.missions.services.assignments import TERMINAL` at line 32. Unused import `MissionStatus` is dropped. The usage at line 91 (`if mission.status in TERMINAL:`) remains unchanged. No circular-import risk evident (API layers safely import from services; services would not import from APIs).

**Minor B — unfilled-seat shape untested** — ADDRESSED at `test_match_api.py:129-154`. New test `test_response_shape_for_unfilled_seat` creates a mission with a requirement for a skill nobody holds, exercises the unfilled-seat path, asserts the dict keys (`{"requirement_id", "skill_name", "min_proficiency", "reason"}`), and asserts `unfilled["reason"] == NO_QUALIFIED_CREW` (line 154) using the imported constant (line 105), not a hardcoded string.

### New Breakage in the Fix Diff

None. All four dataclass fields are enumerated: walk confirms no drops or renames. Nested structures pass through intact. Test coverage is 6/6 focused, 358 overall; `ruff check` clean per report output.

### Out-of-Scope Observations

None.

### Verdict

**Fix round: All findings addressed, no new Critical/Important breakage** — the payload builder enumerates all fields from all four dataclasses without omission; the shape test is unchanged; `TERMINAL` is properly imported; the new unfilled-seat test exercises and asserts the previously-untested path against the exported constant.</result>
<usage><subagent_tokens>25830</subagent_tokens><tool_uses>3</tool_uses><duration_ms>29661</duration_ms></usage>
</task-notification>

- 🔧 **Bash** · `command=sed -n '36,90p' backend/mission_control/missions/apis/matching.py`

<details><summary>⤷ Bash result</summary>

```
"breakdown": member.breakdown,
                "workload_days": member.workload_days,
                "soft_conflicts": member.soft_conflicts,
            }
            for member in result.team
        ],
        "unfilled_seats": [
            {
                "requirement_id": seat.requirement_id,
                "skill_name": seat.skill_name,
                "min_proficiency": seat.min_proficiency,
                "reason": seat.reason,
            }
            for seat in result.unfilled_
… [768 more chars — see the .jsonl]
```

</details>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ echo "=== seats + candidates dict shapes from the engine ===" ⏎ grep -n '"skill_id"\|"skill_name"\|"proficiency"\|"requirement_id"\|"user_id"\|"name"\|"score"\
… [95 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
=== seats + candidates dict shapes from the engine ===
176:        ).values_list("user_id", flat=True)
202:        ).values_list("user_id", "skill_id", "proficiency")
268:                    "requirement_id": seat.requirement_id,
269:                    "skill_name": seat.skill_name,
271:                    "proficiency": proficiency,
361:                        "user_id": user_id,
362:                        "name": name,
363:                        "proficiency": proficiency,
364:
… [36 more chars — see the .jsonl]
```

</details>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ sed -n '264,276p;355,370p' backend/mission_control/missions/services/matching.py ⏎ echo "=== soft_conflicts entry shape (from staffing selector) ===" ⏎ sed -n
… [90 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
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
            RequirementAlternatives(
… [959 more chars — see the .jsonl]
```

</details>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ cat >> .superpowers/sdd/00-overview/progress.md <<'EOF' ⏎ Task 5.2: fix round 1/5 (3 addressed, 0 open; commits bb68e4a..ddd3b94) ⏎ Task 5.2: complete (commits
… [1,622 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
ok
```

</details>

- 🔧 **Agent** · `prompt=You are implementing Task 5.3: Frontend — matcher dialog. ⏎  ⏎ This is task 30 of 33 in the build of "Mission Control", a multi-tenant Django+DRF / React SPA product, and the **last task of Stage 5**. Backend 358
… [8,523 more chars — see the .jsonl]`

<details><summary>⤷ Agent result</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: a40013a22a5d5495a (internal ID - do not mention to user. Use SendMessage with to: 'a40013a22a5d5495a', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do
… [580 more chars — see the .jsonl]
```

</details>

### 🤖 Assistant — 2026-08-12 07:05

**Task 5.2 done** (`ddd3b94`, review clean) — 29/33, backend at **358 tests**. The explicit payload builder is in, and the pre-existing shape test passing unchanged proves the JSON stayed byte-identical for Task 5.3 to parse.

Task 5.3 (matcher dialog) is running — the last task of Stage 5.

## 🧑 User — 2026-08-12 07:16

<task-notification>
<task-id>a40013a22a5d5495a</task-id>
<tool-use-id>toolu_01Jmft6dukmwzXiN2DuvQgxH</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/a40013a22a5d5495a.output</output-file>
<status>completed</status>
<summary>Agent "Implement Task 5.3: matcher dialog UI" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>Committed successfully.

**Status:** DONE
**Commit:** d647711 — "feat: matcher dialog with explanations, swaps, bulk propose"
**Test summary:** Full frontend suite 73/73 passing (66 pre-existing + 7 new matcher tests); `npm run build` and `npm run lint` clean.
**Concerns:** One genuine judgment call flagged in the report — swapping in an alternative unchecks the *whole* member (all their seats), not just the swapped seat, per the brief's literal wording; a per-seat model would need a different data structure than the brief's checkbox-per-member design implies.
**Report:** /Users/samrichards/code/mission-control-mutinex/.superpowers/sdd/00-overview/task-5.3-report.md</result>
<usage><subagent_tokens>154518</subagent_tokens><tool_uses>74</tool_uses><duration_ms>630036</duration_ms></usage>
</task-notification>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ OUT=.superpowers/sdd/00-overview/review-ddd3b94..d647711.diff ⏎ { ⏎   echo "# Review package: ddd3b94..d647711" ⏎   echo; echo "## Commits"; git log --oneline
… [216 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
32667 .superpowers/sdd/00-overview/review-ddd3b94..d647711.diff
```

</details>

- 🔧 **Agent** · `prompt=You are reviewing one task's implementation: first whether it matches its requirements, then whether it is well-built. This is a task-scoped gate, not a merge review — a broad whole-branch review happens separatel
… [7,552 more chars — see the .jsonl]`

<details><summary>⤷ Agent result</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: a0ec421a6101aab3d (internal ID - do not mention to user. Use SendMessage with to: 'a0ec421a6101aab3d', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do
… [580 more chars — see the .jsonl]
```

</details>

### 🤖 Assistant — 2026-08-12 07:22

Task 5.3 committed (`d647711`, 73 frontend tests, build and lint clean). Review running, including a ruling on the flagged swap semantics — swapping one seat currently unchecks the whole member, which matters when a proposed member covers two seats.

## 🧑 User — 2026-08-12 07:26

<task-notification>
<task-id>a0ec421a6101aab3d</task-id>
<tool-use-id>toolu_01T7BfLSS9f9YEkcqS4hJ8qn</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/a0ec421a6101aab3d.output</output-file>
<status>completed</status>
<summary>Agent "Review Task 5.3 (spec + quality)" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>### Spec Compliance
- ❌ Issues found (see Important below): core flow (open → match → team cards with score/breakdown/soft-conflict popovers → swap → propose → staffing panel updates) is implemented per the brief and matches the live contract, but the swap interaction has a real payload-coherence bug and a legibility gap that the review explicitly asked to check.
- ⚠️ Cannot verify from diff: manual smoke test ("seeded org → mission → Auto-match → swap → propose → roster fills") — report claims it but no evidence beyond automated tests is in the diff.

### Strengths
- Correctly overrides the brief's stale `breakdown: {proficiency, workload, soft_conflict}` shorthand with the live backend field names (`proficiency_fit`, `workload_balance`, `soft_conflict_penalty`), per the STANDING RULE, and documents the divergence (`frontend/src/features/matching/api/matching.ts:131-151`).
- Reuses the existing `useProposeAssignments` (Stage 4) rather than a second propose path (`match-dialog.tsx:252`, `:340`); confirmed its `onSuccess` invalidates both `["missions", missionId, "staffing"]` and `["missions", missionId]` (`frontend/src/features/assignments/api/assignments.ts:75-78, 84-91`) — staffing panel goes stale-free.
- Full response tree is zod-parsed, including `seats`, `breakdown`, `soft_conflicts`, `candidates` (`matching.ts:140-219`); `UnfilledSeat.reason` is a closed `z.enum` of the four constants, so a fifth value throws rather than silently rendering (`matching.ts:178-196`; confirmed `errorMessage()` at `frontend/src/lib/api-errors.ts:27-39` degrades a non-Axios/Zod error to a generic message, not a swallow).
- `score` and `breakdown` are genuinely surfaced (inline "Score N" + Popover with fit/workload/conflict), not fetched-and-discarded (`match-dialog.tsx:387-398`).
- Gating is correct and uses the shared `hasPermission`: matcher on `match.run` + mission non-terminal (`staffing-panel.tsx:57`), propose on `assignment.manage` (`match-dialog.tsx:283`, `:483`).
- Both 400 paths (terminal-mission match refusal, propose refusal) surface the server's `message`, with dedicated tests (`matching.test.tsx:624-656`).
- Correctly caught and fixed a real collision the brief didn't anticipate: keying swaps by `requirement_id:holder_user_id` rather than `requirement_id` alone, for the `required_count &gt; 1` case (`match-dialog.tsx` swap map comment + `swapKey`, diff lines 263-273).
- Verified via TanStack Query source (`query-core/src/mutation.ts:352-361`) that a mutation's `data` resets to `undefined` on a new `pending` dispatch — so re-run/reopen never overlaps a stale team with the "Matching…" loading state.
- No client-side re-implementation of availability/scoring logic — `team`/`alternatives` rendered as-is.

### Issues

#### Important (Should Fix)
1. **Re-swapping the same seat to a different alternative leaves the previously-swapped candidate silently selected, producing an incoherent propose payload.** `match-dialog.tsx:430-433` always calls `handleSwap(seat.requirement_id, member.user_id, value)` — `member.user_id` is fixed to the *original matcher-proposed holder*, never the currently swapped-in candidate. In `handleSwap` (`match-dialog.tsx:318-334`) the delete/add pair is `next.delete(holderUserId); next.add(candidate.user_id)`. On a **second** swap of the same seat (choose candidate A, then reconsider and choose candidate B — realistic whenever a requirement has 2+ alternatives), `holderUserId` is still the original holder, already removed on the first swap, so the delete is a no-op and candidate A's id is *never removed*. Result: `selected` ends up containing both A and B, the footer's "Propose N assignments" count is inflated by the phantom entry, and there is no card or badge anywhere for candidate A (only `result.team` members get cards) — the lead cannot see who the extra person is. This is exactly the payload-coherence question this review was asked to check, and it's untested: the only fixture used (`twoMemberMatch`) gives the Piloting requirement a single alternative candidate, so a second swap on the same seat is never exercised (`matching.test.tsx:552-559`). Fix: track `holderUserId` as "whoever currently fills this seat" (update it after each swap, or key deletion off `swap?.user_id ?? member.user_id`) so re-swapping removes the prior candidate.
2. **Swapping out a member who covers a second, unrelated seat silently drops coverage for that seat with no visual signal.** Confirmed unchecking (`selected.has(member.user_id)`, `match-dialog.tsx:381`) is used only to drive the checkbox's `checked` prop — no other styling in the card (`match-dialog.tsx:376` `&lt;li&gt;` className is static) reflects selection state. When a swap unchecks a multi-seat member (the implementer's flagged judgment call, report item 4), that member's other seat badges keep rendering exactly as before, with no dimming, "not proposed" marker, or any indicator that the seat is now unpropoosed. `result.unfilled_seats` is also never recomputed client-side, so the orphaned seat doesn't move there either. Multi-seat coverage by one generalist crew member is a core scenario for this matcher (Stage 5's exit criteria explicitly calls out "matcher demonstrably picks generalists"), so this isn't an edge case. The stated rationale ("literal checkbox-per-member reading") doesn't resolve the legibility failure the review asked about — a lead has no way to see what happened. Fix: at minimum visually mute/gray an unchecked member's card (and its seat rows), so the lead can see exactly what will and won't be proposed.

#### Minor (Nice to Have)
- `matching.ts`'s `SoftConflictSchema` duplicates `assignments.ts`'s identical schema (`matching.ts:157-162` vs `assignments.ts:31-35`), and `staffing-panel.tsx:38`'s `TERMINAL_STATUSES` duplicates an unexported constant from `transition-buttons.tsx`. Both are justified in comments and are harmless, but the report's claim that this duplication follows "the constraints file's known limitation precedent" overstates it — the constraints file's only documented precedent is about UI pagination, not general constant duplication. Not a code defect, just a slightly inflated justification.
- `assignment.manage`-without-`match.run` gating on the Propose button (`match-dialog.tsx:283, :483`) is implemented but has no dedicated test; report acknowledges this and notes it's currently unreachable given the role catalog. Low risk, but the double-swap bug above shows that "the fixture never exercised it" is exactly how bugs like this survive.
- `open_capacity` is parsed but never rendered anywhere in the dialog — not required by the brief, but a lead running Auto-match with an unfilled seat might reasonably want to see remaining capacity alongside the reason.
- Raw `score` is displayed unrounded (e.g., "Score 1.2000000001" is possible depending on backend float formatting) — cosmetic only.

### Assessment
**Task quality:** Needs fixes
**Reasoning:** The propose/permission/error-surfacing/reuse fundamentals are solid and the implementer caught a real edge case (same-requirement multi-holder swap keying) that the brief didn't anticipate. But a second, unaddressed swap-state bug (re-swapping the same seat leaves a phantom candidate selected) produces an incoherent `user_ids` payload under a realistic interaction, and the whole-member-uncheck behavior lacks any visual signal that a second seat's coverage silently dropped — both go directly to the "is the resulting payload coherent and legible" question this review was scoped to answer, so this task should not be considered done until at least the double-swap bug is fixed.</result>
<usage><subagent_tokens>73430</subagent_tokens><tool_uses>11</tool_uses><duration_ms>251057</duration_ms></usage>
</task-notification>

- 🔧 **SendMessage** · `{"to": "a40013a22a5d5495a", "summary": "Task 5.3 fix round 1: double-swap bug + legibility", "message": "Task 5.3 review came back \"Needs fixes\" with two Important findings, both about swap state. Fix both, re-run the
… [4,434 more chars — see the .jsonl]`

<details><summary>⤷ SendMessage result</summary>

```
{"success":true,"message":"Agent \"a40013a22a5d5495a\" had no active task; resumed from transcript in the background with your message. You'll be notified when it finishes. Output: /private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/a40013a22a5d5495a.output","resumedAgentId":"a40013a22a5d5495a","pin":{"id":"a40013a22a5d5495a","name":"a40013a22a5d5495a","ref":"e3a9f2"}}
```

</details>

### 🤖 Assistant — 2026-08-12 07:27

Good catch from that reviewer. The matcher dialog had a genuine state bug: swapping a seat twice — pick one alternative, reconsider, pick another — left the first candidate still selected, because the code always deleted the *original* proposed holder rather than whoever currently fills the seat. The result is an inflated proposal containing someone with no card in the UI, so the lead can't see or remove them. It survived because the test fixture only ever gave one requirement a single alternative.

The second finding is subtler but real: unchecking a member is reflected only in a checkbox prop, so when a swap drops a generalist who was covering two seats, the second seat's coverage vanishes with no visual signal at all.

## 🧑 User — 2026-08-12 07:31

<task-notification>
<task-id>a40013a22a5d5495a</task-id>
<tool-use-id>toolu_01DVNZgNrCmntfRuxZu1aEso</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/a40013a22a5d5495a.output</output-file>
<status>completed</status>
<summary>Agent "Implement Task 5.3: matcher dialog UI" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>**Status:** DONE
**Commits:** d647711 "feat: matcher dialog with explanations, swaps, bulk propose"; 8802e17 "fix: correct swap-holder tracking and surface unchecked-member state"
**Test summary:** Full frontend suite 75/75 passing (73 prior + 2 new regression tests for the two findings); `npm run build` and `npm run lint` clean; no warnings/act()/unhandled-request noise.
**Concerns:** None — both Important findings fixed and covered by dedicated regression tests; report's mis-cited precedent also corrected.
**Report:** /Users/samrichards/code/mission-control-mutinex/.superpowers/sdd/00-overview/task-5.3-report.md</result>
<usage><subagent_tokens>186431</subagent_tokens><tool_uses>27</tool_uses><duration_ms>243835</duration_ms></usage>
</task-notification>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ OUT=.superpowers/sdd/00-overview/review-d647711..8802e17.diff ⏎ { ⏎   echo "# Review package: d647711..8802e17" ⏎   echo; echo "## Commits"; git log --oneline
… [216 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
19512 .superpowers/sdd/00-overview/review-d647711..8802e17.diff
```

</details>

- 🔧 **Agent** · `prompt=You are re-reviewing one task's fix round. A previous review produced findings; an implementer has attempted to fix them. Your job is to verdict each finding and inspect the fix diff — nothing else. ⏎  ⏎ ## The Ta
… [5,153 more chars — see the .jsonl]`

<details><summary>⤷ Agent result</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: a4514040bf58681e4 (internal ID - do not mention to user. Use SendMessage with to: 'a4514040bf58681e4', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do
… [580 more chars — see the .jsonl]
```

</details>

### 🤖 Assistant — 2026-08-12 07:32

Task 5.3 fixes committed (`8802e17`, 75 frontend tests). Re-review running — swap state is fiddly enough that a partial fix reads like a complete one, so I've asked it to walk five specific sequences including swapping a seat back to the originally-proposed member.

## 🧑 User — 2026-08-12 07:35

<task-notification>
<task-id>a4514040bf58681e4</task-id>
<tool-use-id>toolu_01JRi3vhMZ4bRpeiaLTbCumL</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/a4514040bf58681e4.output</output-file>
<status>completed</status>
<summary>Agent "Re-review Task 5.3 fix round 1" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>### Finding Verdicts

- **Important 1 — re-swapping the same seat leaves a phantom candidate selected.** ADDRESSED. `match-dialog.tsx:91-112` now separates `slotOwnerUserId` (stable map key) from `currentHolderUserId` (computed per-seat at `match-dialog.tsx:217-222` as `swap ? swap.user_id : member.user_id`), and `handleSwap` deletes `currentHolderUserId` (line 104), not the original holder. Regression test added: `matching.test.tsx:314-350` swaps Priya→Jae Kim→Lee Zhao and asserts the payload is exactly `{user_ids:[4,6]}` with "Propose 2 assignments" (not 3). Fixture `twoMemberMatch.alternatives[0].candidates` was widened to two candidates (`matching.test.tsx:247-253`), satisfying the "two alternatives on one requirement" requirement. Traced against pre-fix code: the old `handleSwap` always deleted `member.user_id` (Priya, id 3), so the second swap's delete would be a no-op and the old payload would be `{user_ids:[4,5,6]}` — the new test genuinely discriminates old vs. new behavior.

- **Important 2 — unchecked member's card visually identical to checked.** ADDRESSED. `match-dialog.tsx:158-167` applies `border-dashed opacity-60` via `cn()` when `!isSelected`, and `match-dialog.tsx:179-181` renders an explicit `(not proposed)` text marker. The new test (`matching.test.tsx:352-373`, `generalistMatch` fixture at 265-291) asserts the marker text is present/absent (not just the checkbox prop) and that the still-covered Navigation badge remains visible but the card is marked stale — a real, user-perceivable assertion.

- **Small A — round the displayed score.** ADDRESSED. `match-dialog.tsx:184`: `Score {member.score.toFixed(2)}`.

- **Small B — correct the mis-cited precedent.** ADDRESSED. `task-5.3-report.md:20` now states the duplication "is justified on its own merits... not by any constraints-file precedent" and explains the earlier mis-citation was about UI pagination, unrelated to this case.

### New Breakage in the Fix Diff

None. The diff is scoped to the two findings plus the two small items; `useProposeAssignments` call, the `z.enum` reason schema (untouched, not even in this diff), 400-message surfacing (`handlePropose` catch block unchanged), and the `requirement_id:holder_user_id` swap-keying scheme for `required_count &gt; 1` (still keyed the same way, just documented more precisely) are all preserved.

Walked the required sequences against the new code:
- Swap once: correct (holder removed, candidate added).
- Swap twice same seat: correct (tested).
- Two different seats on the same multi-seat member (generalist case), each swapped independently: correct — each seat's `currentHolderUserId` is derived from its own `swaps[requirementId:memberId]` entry, so both swaps clear only their own holder.
- Swap a seat back to the *originally-proposed* member: not reachable through the UI at all — the backend's `alternatives` list is built from the pool with team members already popped out (`backend/mission_control/missions/services/matching.py:341-343` comment: "already proposed... popped from the pool"), so the original holder is never offered as a swap target. This isn't a regression from this diff, just a pre-existing UI limitation (no "revert" affordance).
- Swap a seat, then manually re-check the original holder's own checkbox: **not handled correctly**. `toggleMember` (`match-dialog.tsx:76-83`, untouched by this diff) only adds/removes the clicked `userId`; it has no knowledge of `swaps`. Re-checking the original holder after a swap adds them back to `selected` while the swapped-in candidate stays in `selected` too, so the resulting `user_ids` contains **both** people for one seat with no orphan-removal and no visual contradiction flagged (the card looks fully normal/checked again, even though its own "Swapped in: X" badge still shows someone else holding that seat). This bug is not introduced by this diff (the pre-fix code had the identical gap, since `toggleMember` was never touched in either round), so it does not count as new breakage, but it means the "new holder tracking" still does not handle every requested sequence.

### Out-of-Scope Observations

- The manual-recheck-after-swap double-selection gap described above (`match-dialog.tsx:76-83` `toggleMember` vs. the `swaps` state introduced/refined at `match-dialog.tsx:91-112`, `217-222`) is a real, easily-triggered correctness issue (duplicate seat coverage silently included in the propose payload) but predates this fix diff and wasn't part of either Important finding's required fix — flagging for a possible follow-up finding, not blocking this round.
- Breakdown values in the popover (`Fit: {member.breakdown.proficiency_fit}` etc., `match-dialog.tsx:188-190`) remain unrounded — Small A only asked for the main `score`, so this is not a gap in this round.

### Verdict

**Fix round:** All findings addressed, no new Critical/Important breakage. (One pre-existing, out-of-round gap noted above — manual re-check of a swapped-out original holder's checkbox produces a duplicate-selection state — worth a follow-up finding but does not reopen Important 1 or 2 as reported.)</result>
<usage><subagent_tokens>55668</subagent_tokens><tool_uses>5</tool_uses><duration_ms>173241</duration_ms></usage>
</task-notification>

### 🤖 Assistant — 2026-08-12 07:35

The re-reviewer cleared both findings but surfaced a third bug of the same class, in this task's own code — worth one more round rather than shipping it.

- 🔧 **SendMessage** · `{"to": "a40013a22a5d5495a", "summary": "Task 5.3 fix round 2: recheck-after-swap duplicate", "message": "Both Important findings verified fixed — the re-reviewer traced your new `slotOwnerUserId` / `currentHolderUserId`
… [3,095 more chars — see the .jsonl]`

<details><summary>⤷ SendMessage result</summary>

```
{"success":true,"message":"Agent \"a40013a22a5d5495a\" had no active task; resumed from transcript in the background with your message. You'll be notified when it finishes. Output: /private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/a40013a22a5d5495a.output","resumedAgentId":"a40013a22a5d5495a","pin":{"id":"a40013a22a5d5495a","name":"a40013a22a5d5495a","ref":"e3a9f2"}}
```

</details>

### 🤖 Assistant — 2026-08-12 07:35

Both original findings are verified fixed, but the re-review surfaced a third bug of the same family: swap a member out, then click their checkbox to bring them back, and the payload now contains *both* them and the swapped-in candidate for one seat — with the card rendering as normally checked while still showing a contradicting "Swapped in" badge.

Strictly that's an out-of-round observation I could have parked. I'm spending one more round on it because it's trivially reachable by a lead who changes their mind, it silently produces a wrong proposal in the product's headline feature, and the likely fix also gives the UI the "revert a swap" affordance it currently lacks entirely.

## 🧑 User — 2026-08-12 07:38

<task-notification>
<task-id>a40013a22a5d5495a</task-id>
<tool-use-id>toolu_012MHgSpsH9fZUuZKgh8PjSE</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/a40013a22a5d5495a.output</output-file>
<status>completed</status>
<summary>Agent "Implement Task 5.3: matcher dialog UI" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>**Status:** DONE
**Commits:** d647711 "feat: matcher dialog with explanations, swaps, bulk propose"; 8802e17 "fix: correct swap-holder tracking and surface unchecked-member state"; dd0005f "fix: revert a member's swap on re-check instead of double-covering the seat"
**Test summary:** Full frontend suite 76/76 passing (75 prior + 1 new regression test, verified to genuinely fail against the pre-fix code before restoring); `npm run build` and `npm run lint` clean; no warnings/act()/unhandled-request noise.
**Concerns:** None — the fix chose "re-check reverts the swap" (reviewer's preferred option) and includes a guard for the edge case where a swapped-in candidate covers two different reverted seats simultaneously.
**Report:** /Users/samrichards/code/mission-control-mutinex/.superpowers/sdd/00-overview/task-5.3-report.md</result>
<usage><subagent_tokens>215556</subagent_tokens><tool_uses>16</tool_uses><duration_ms>193095</duration_ms></usage>
</task-notification>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ OUT=.superpowers/sdd/00-overview/review-8802e17..dd0005f.diff ⏎ { ⏎   echo "# Review package: 8802e17..dd0005f" ⏎   echo; echo "## Commits"; git log --oneline
… [216 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
12719 .superpowers/sdd/00-overview/review-8802e17..dd0005f.diff
```

</details>

- 🔧 **Agent** · `prompt=You are re-reviewing one task's second fix round. Your job is to verdict the finding and inspect the fix diff — nothing else. ⏎  ⏎ ## The Task ⏎  ⏎ Read the task brief: /Users/samrichards/code/mission-control-muti
… [4,537 more chars — see the .jsonl]`

<details><summary>⤷ Agent result</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: a1192eb20477806f4 (internal ID - do not mention to user. Use SendMessage with to: 'a1192eb20477806f4', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do
… [580 more chars — see the .jsonl]
```

</details>

### 🤖 Assistant — 2026-08-12 07:39

Fix committed (`dd0005f`, 76 tests) — re-checking a member now reverts their swap, which also gives the dialog the revert affordance it lacked. Since this is the third swap-state fix, I've set the bar at "coherent under every sequence" and given the re-reviewer five specific paths to walk, including the same candidate swapped into two seats with one reverted.

## 🧑 User — 2026-08-12 07:41

<task-notification>
<task-id>a1192eb20477806f4</task-id>
<tool-use-id>toolu_018vZTjj7CABzanbN7s3vcPW</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/a1192eb20477806f4.output</output-file>
<status>completed</status>
<summary>Agent "Re-review Task 5.3 fix round 2" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>Type confirmed: `ProposedMember` is exported and `member.seats` matches usage. Everything checks out. Now finalizing verdict.

## Finding Verdicts

- **Manually re-checking a swapped-out member duplicates coverage for one seat** — ADDRESSED. `frontend/src/features/matching/components/match-dialog.tsx:85-129` (`toggleMember`) now takes the full `ProposedMember`, and on re-check finds all `swaps` entries keyed by this member's seats, removes the swapped-in candidate(s) from `selected` (unless still needed elsewhere), deletes the corresponding `swaps` entries, and adds the member back. Covering test at `matching.test.tsx:196-235` exercises swap→re-check and asserts `posted === {user_ids: [4, 3]}` (Priya + Sam, no Jae Kim), checkbox re-checked, no stale "Swapped in" badge, no "(not proposed)" text.

## Sequence walkthroughs (traced against the code)

- **(a) swap S→C, re-check M**: `keysToClear=[key(S,M)]`, no surviving swaps, `candidateIdsToDrop=[C]`. Result: `selected` drops C, adds M; `swaps` entry deleted. `user_ids` = original team. Matches expectation.
- **(b) deselecting a swapped-in candidate C directly**: confirmed — C never gets its own card (only `result.team` renders cards), so the *only* path to remove C is re-checking the original slot owner, which reverts the swap. No direct "uncheck C" affordance exists; this is the deliberate design choice from the finding ("re-check reverts the swap" preferred option), not a gap introduced here.
- **(c) M covers S1+S2, both swapped to different candidates C1/C2, then M re-checked**: `keysToClear=[key(S1,M), key(S2,M)]`, no survivors, `candidateIdsToDrop=[C1,C2]`. Both dropped, M re-added, both swap entries deleted. Coherent — both seats revert together.
- **(d) same candidate C swapped into two different seats (owned by M1 and M2), then M1 reverted**: `keysToClear=[key(S1,M1)]` only (M2's seat key isn't among M1's `member.seats`). `survivingCandidateIds` is built from the *other* swap entries (`key(S2,M2): C`), so it contains C's id. `candidateIdsToDrop` filters C out since C survives. Result: C stays selected (still covers S2), M1 re-added, only S1's swap entry cleared. The implementer's claimed guard checks out — verified by hand-tracing, not just trusting the report.
- **(e) swap, revert, swap again**: after revert, `swaps[key(S,M)]` is gone, so `currentHolderUserId` computed at render is back to `M.user_id`; a fresh swap via `handleSwap` correctly removes M and adds the new candidate. No residue from the first swap.

Badge consistency: reverting deletes the `swaps` entry, so `swap` look-up at render (`match-dialog.tsx:274-278`) returns `undefined` and the "Swapped in" badge disappears — card is self-consistent (checked, no contradicting badge, no "(not proposed)").

## Test genuineness

The new test (`matching.test.tsx:196-235`) asserts checkbox-checked, absence of "Swapped in" badge, absence of "(not proposed)", footer count, and posted `user_ids`. Implementer's quoted RED run reverting `toggleMember` shows failure specifically on the "no Swapped in badge" assertion (`found &lt;span&gt;Swapped in: Jae Kim&lt;/span&gt;`) — genuine: under old code the checkbox-checked assertion alone would have passed (old code still added M back to `selected`), but the badge/payload assertions would not, so the test does depend on the fix, not just superficially. Confirmed by tracing: old `toggleMember` never touched `swaps`, so the stale badge and the extra id in the payload are real discriminators.

## Breakdown rounding

Confirmed: `match-dialog.tsx:168-170` now uses `.toFixed(2)` for `proficiency_fit`, `workload_balance`, `soft_conflict_penalty` in the popover.

## Prior fixes / behaviors disturbed by this diff

- `currentHolderUserId` tracking / `handleSwap` (round 1, Finding 1) — untouched (diff shows no changes inside `handleSwap`; only `toggleMember`'s call site changed from `toggleMember(member.user_id)` to `toggleMember(member)`).
- `(not proposed)` marker (round 1, Finding 2) — untouched, still driven by `isSelected`.
- `useProposeAssignments` reuse/invalidation, `z.enum` on `reason`, 400-message surfacing — none of these files/lines are in the diff; not disturbed.

## New Breakage in the Fix Diff

None found.

## Out-of-Scope Observations

- Directly unchecking a member who is *also* the swapped-in candidate for another seat (e.g., original team member B is swapped into a different member A's seat, then B's own checkbox is unchecked) would remove B from `selected` without clearing the `swaps[key(S,A)]` entry — A's card would still show "Swapped in: B" even though B is no longer in the payload. This is a latent inconsistency in the *unchecking* branch of `toggleMember`, which is byte-for-byte unchanged by this diff (pre-existing from round 1, not introduced here). Whether it's reachable depends on whether `alternatives` can ever surface an existing team member as a candidate for another seat — not verified, flagged for a future round if relevant. Does not block this round.

### Verdict
**Fix round:** All findings addressed, no new Critical/Important breakage.</result>
<usage><subagent_tokens>45681</subagent_tokens><tool_uses>5</tool_uses><duration_ms>90846</duration_ms></usage>
</task-notification>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ sed -n '335,352p' backend/mission_control/missions/services/matching.py`

<details><summary>⤷ Bash result</summary>

```
for _ in range(seat.open_count)
        )

    # 7. Alternatives: the bench for each requirement — qualified, available, and not
    #    already proposed (the team members were popped from the pool as they were
    #    taken). Scored as if they took this one seat, so the number shown explains the
    #    order; ties break on ascending user id like everywhere else.
    alternatives: list[RequirementAlternatives] = []
    for cov in coverage.requirements:
        ranked_bench = []
        for u
… [385 more chars — see the .jsonl]
```

</details>

### 🤖 Assistant — 2026-08-12 07:41

Confirmed unreachable — that closes the last observation.

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex/backend && uv run pytest 2>&1 | tail -2 && uv run ruff check . 2>&1 | tail -1 ⏎ cd ../frontend && npm test -- --run 2>&1 | grep -E 'Test Files|Tests ' && npm run
… [42 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
......................................................................   [100%]
358 passed in 83.08s (0:01:23)
All checks passed!
 Test Files  10 passed (10)
      Tests  76 passed (76)
✓ built in 1.53s
```

</details>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ docker compose -f docker-compose.dev.yml up -d backend >/dev/null 2>&1 ⏎ for i in $(seq 1 40); do curl -s -o /dev/null http://localhost:8000/api/v1/skills/ 2>/
… [1,321 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
=== run the matcher ===
{
    "team": [
        {
            "user_id": 6,
            "name": "Crew1 Meridian",
            "seats": [
                {
                    "requirement_id": 17,
                    "skill_name": "Orbital Welding",
                    "min_proficiency": 5,
                    "proficiency": 7
                }
            ],
            "score": 0.722,
            "breakdown": {
                "proficiency_fit": 0.222,
                "workload_balance": 1.0,
… [511 more chars — see the .jsonl]
```

</details>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ docker compose -f docker-compose.dev.yml stop backend >/dev/null 2>&1 ⏎ cat >> .superpowers/sdd/00-overview/progress.md <<'EOF' ⏎ Task 5.3: fix round 1/5 (2 ad
… [2,437 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
ok
```

</details>

- 🔧 **Agent** · `prompt=You are implementing Task 6.1: Dashboard selectors. ⏎  ⏎ This is task 31 of 33 in the build of "Mission Control", a multi-tenant Django+DRF / React SPA product, and the first task of Stage 6 — the final stage. Sta
… [8,193 more chars — see the .jsonl]`

<details><summary>⤷ Agent result</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: a9ee0b8ee76cb3e45 (internal ID - do not mention to user. Use SendMessage with to: 'a9ee0b8ee76cb3e45', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do
… [580 more chars — see the .jsonl]
```

</details>

### 🤖 Assistant — 2026-08-12 07:44

## Stage 5 complete — 30/33 tasks

**Backend 358 tests + ruff clean, frontend 76 tests, build clean.** I ran the matcher live and it returned a real pick with a full explanation: `score 0.722`, breakdown `{proficiency_fit 0.222, workload_balance 1.0, soft_conflict_penalty 0.0}`. That arithmetic checks out exactly against the documented formula — `1.0×0.222 + 0.5×1.0 − 0.75×0` — so the engine, the API serializer and the scoring contract all agree end to end.

Task 5.3 took two fix rounds and found three bugs of the same family, all producing an incoherent proposal: a phantom candidate after re-swapping, invisible loss of a generalist's second seat, and double-coverage after re-checking. The second round was discretionary on my part — the third bug was technically out of round — but it was trivially reachable in the headline feature, and the fix also gave the dialog a revert affordance it had been missing entirely.

Stage 6, the final stage, has begun with the dashboard selectors.

## 🧑 User — 2026-08-12 07:55

<task-notification>
<task-id>a9ee0b8ee76cb3e45</task-id>
<tool-use-id>toolu_014kG2yxq32QB2r9opv2qQAe</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/a9ee0b8ee76cb3e45.output</output-file>
<status>completed</status>
<summary>Agent "Implement Task 6.1: dashboard selectors" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>Committed successfully.

**Status:** DONE_WITH_CONCERNS
- Commit: fe26dd7 "feat: dashboard selectors — pipeline, readiness, utilization, skill gaps"
- Test summary: 373/373 backend tests passing (358 pre-existing + 15 new), ruff clean repo-wide
- Concern: `staffing_readiness` calls `mission_coverage` once per currently-live mission (pending_approval/approved/active, not-ended) — O(N) in that bounded working set, not O(1) like the other three selectors. I deliberately kept this (it's the brief's stated "Consumes: mission_coverage" interface, and vectorizing the greedy per-skill fill logic in SQL would restate business logic owned elsewhere), but measured and asserted the exact `1 + 3*N` formula at two mission counts rather than assuming it's fine. Also diverged from the brief's sample code in three places (documented in the report) to avoid N+1 queries and forbidden literal availability-rule patterns that the brief's own sample code contained.
- Report: `/Users/samrichards/code/mission-control-mutinex/.superpowers/sdd/00-overview/task-6.1-report.md` (note: this path is gitignored, so it wasn't included in the commit)</result>
<usage><subagent_tokens>108946</subagent_tokens><tool_uses>44</tool_uses><duration_ms>680050</duration_ms></usage>
</task-notification>

- 🔧 **Bash** · `command="/Users/samrichards/.claude/plugins/cache/claude-plugins-official/superpowers/6.2.0/skills/subagent-driven-development/scripts/review-package" /Users/samrichards/code/mission-control-mutinex/docs/superpowers/plan
… [59 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
wrote /Users/samrichards/code/mission-control-mutinex/.superpowers/sdd/00-overview/review-dd0005f..fe26dd7.diff: 1 commit(s), 27293 bytes
```

</details>

- 🔧 **Agent** · `prompt=You are reviewing one task's implementation: first whether it matches its requirements, then whether it is well-built. This is a task-scoped gate, not a merge review — a broad whole-branch review happens separatel
… [7,101 more chars — see the .jsonl]`

<details><summary>⤷ Agent result</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: aca92266ec458a3e4 (internal ID - do not mention to user. Use SendMessage with to: 'aca92266ec458a3e4', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do
… [580 more chars — see the .jsonl]
```

</details>

### 🤖 Assistant — 2026-08-12 07:56

Task 6.1 committed (`fe26dd7`, 373/373) but reported **DONE_WITH_CONCERNS**: one selector calls `mission_coverage` once per live mission, so it's `1 + 3N` queries rather than constant. The implementer kept it deliberately and measured the exact formula at two mission counts rather than assuming.

That's exactly the defect I warned this task about, so I've asked the reviewer to rule plainly on whether it's a justified exception or an N+1 dressed up as a feature.

## 🧑 User — 2026-08-12 08:00

<task-notification>
<task-id>aca92266ec458a3e4</task-id>
<tool-use-id>toolu_01C16pnyX7Ew9rkxTs8bBqBB</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/aca92266ec458a3e4.output</output-file>
<status>completed</status>
<summary>Agent "Review Task 6.1 (spec + quality)" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>Good, offsets confirmed. Now I have everything needed for the report.

### Spec Compliance
- ✅ Spec compliant. All four selectors are implemented, tenant-scoped, read-only, and match the brief's field-level definitions. Verified by reading `backend/mission_control/missions/selectors/dashboard.py` in full against the brief's interface spec (task-6.1-brief.md:8-11) and cross-checking the metric formulas against `backend/mission_control/missions/selectors/staffing.py`.
- ⚠️ Cannot verify: the report's claim of a brief "dominant risk" section warning against calling `mission_coverage` in a loop. `task-6.1-brief.md` (the only brief text available to this review) contains no such section — only Files/Interfaces/Steps. This may have existed in a fuller `06-dashboard-polish.md` not present in `.superpowers/sdd/00-overview/`. Doesn't change the ruling below, since the brief's own Step-3 sample code independently does exactly this loop.

### Strengths
- The three disclosed divergences from the brief's sample are all real, necessary, and correctly implemented:
  - `pipeline_summary` (dashboard.py:60-92): correlated `Subquery`/`OuterRef`/`Coalesce` replaces the sample's per-mission transition lookup — 3 queries total, verified constant at 2 vs. 10+20 missions (test_dashboard.py: `test_pipeline_summary_query_count_is_constant`, diff:384-413).
  - `skill_gaps` (dashboard.py:200-247): one grouped `Sum`/`Min` aggregate plus one batched `CrewSkill` fetch replaces a per-skill count query — 2 queries constant at 2 vs. 15 skills (`test_skill_gaps_query_count_is_constant`, diff:685-708).
  - `crew_utilization` (dashboard.py:158-197): calls `committed_assignments` (staffing.py:85-109) instead of restating the overlap test/status literal. Verified this is semantically identical to the brief's own definition — "accepted assignment-days on approved/active missions" is exactly the hard-block predicate — so reuse is correct, not just literal-avoidance theatre. 2 queries constant (`test_utilization_query_count_is_constant`, diff:602-620).
- Grepped the diff for `start_date__lte`, `end_date__gte`, and literal `{approved, active}`-shaped sets outside comments: none found in code (diff:117, 145, 228 are docstring/comment mentions only, deliberately negated via `.exclude(...__lt=...)`/`.exclude(...__gt=...)`). Confirms the report's self-review claim.
- Empty-organisation case returns real zeros/empty lists for all four functions, not `None`s or errors (`test_empty_organisation_returns_zeros_not_errors`, diff:310-322) — verified against the code: `dict.fromkeys(MissionStatus.values, 0)` (dashboard.py:80), `if rows else 0` guard on `org_utilization_pct` (dashboard.py:190-192), `if not requirement_rows: return []` (dashboard.py:216-217).
- Tenancy: the one non-tenant-scoped model (`User`) is explicitly filtered with `tenant_id=require_current_tenant_id()` (dashboard.py:161-163), matching the established interface fact. `CrewSkill` queries rely correctly on its own fail-closed manager plus composite-FK tenant coherence rather than needing an explicit `user__tenant_id` filter.
- Tests assert real computed values throughout (exact dicts, percentages, counts — e.g. diff:640-646, diff:568-570), not shape-only. Query counts asserted at two data sizes for every selector, including a scaling-formula test for the non-constant one (diff:505-549).
- No API/serializers/UI, no `objects_unscoped` in application code (only in tests, matching the brief's own given sample) — no Task 6.2 scope creep.

### Issues

#### Important (Should Fix) — plan-mandated, not a code defect
- **`staffing_readiness` calls `mission_coverage` once per live mission — genuine O(N), not O(1)** (dashboard.py:118-152, loop at dashboard.py:134-152). Ruling on the concern as requested:
  - **Real defect or justified exception: justified exception, not a fix-now defect.** The brief's own Step-3 sample code (task-6.1-brief.md:158-176) does the identical per-mission loop, and the interface line explicitly names `mission_coverage` as this function's sole data source (task-6.1-brief.md:12). Per the STANDING RULE, sample code only yields to a *Global Constraint* it contradicts — there is no global constraint mandating O(1) dashboard queries, so the brief's design stands.
  - **Is the working set genuinely bounded?** Only relative to full mission history, not to a constant: N excludes draft/completed/cancelled/rejected (verified via `test_readiness_query_count_scales_with_relevant_missions_only`, diff:505-549, which proves 10 irrelevant missions add zero queries), but N still grows linearly with the organisation's *concurrent* mission load — a busy tenant with 200 simultaneously live missions means ~601 queries on one dashboard call. This is a real, not hypothetical, scaling risk.
  - **Would vectorising duplicate the greedy semantics?** Yes, for `filled_count`/`fully_covered` specifically — the per-skill, most-demanding-row-first, one-seat-per-skill allocation (staffing.py:193-263) is real business logic, and re-deriving it in SQL would violate the "consume, never restate" instruction that names `mission_coverage` explicitly. `total_seats`/`accepted_count` could be bulk-aggregated without touching that logic, but `at_risk` needs `fully_covered` for every row, so that doesn't avoid the per-mission call in practice. A true fix requires a *batched* selector inside `staffing.py` (e.g. `mission_coverage_batch(missions)` doing the same 3-ish queries total) — out of scope for Task 6.1's file list (only `dashboard.py`/`test_dashboard.py`).
  - **Is asserting `1+3N` at two sizes honest treatment or dressing-up?** Honest treatment — it's measured, tested at two sizes, and explicitly flagged as a concern in the report rather than buried. Not silently accepted as O(1).
  - **Verdict:** not a defect to send back on this task; it is the brief's specified design, correctly implemented and honestly disclosed. It should be tracked as a forward-looking limitation (e.g. batching `mission_coverage` in a later `staffing.py` change) rather than blocking this task's approval.

#### Minor (Nice to Have)
- Report's "the exact formula (`1 + 3*N`)" (task-6.1-report.md:76-77) overstates precision: `mission_coverage` only costs 3 queries when a mission has both requirements and accepted crew (staffing.py:216 guards the third query on `if requirements and accepted_users`); a mission with neither costs 2. The test deliberately constructs every "relevant" mission to hit the 3-query path (diff:516-531), so `1+3N` is a verified *worst case*, not a universal exact formula. Wording nit only — the underlying test and code are correct.
- `org_utilization_pct` (dashboard.py:190-192) averages already-rounded per-crew `utilization_pct` values rather than `total_assigned_days / (crew_count * window_days)`. Mathematically these coincide before rounding (same denominator per crew member), but double-rounding can drift by a point in unlucky cases. Brief doesn't specify the formula, and the given test passes either way — not worth reopening, just noting for anyone tightening this metric later.

### Assessment
**Task quality:** Approved
**Reasoning:** All four selectors match the brief's field-level definitions, are correctly tenant-scoped, handle the empty-organisation case cleanly, and demonstrate real query-count discipline for three of the four (verified against `staffing.py`, not just trusted from the report). The one non-constant selector (`staffing_readiness`) is a brief-mandated design (its own sample code does the same loop, and the interface note names `mission_coverage` as the sole source), correctly measured and disclosed rather than hidden — a legitimate exception under the STANDING RULE, not a defect requiring rework in this task's scope.</result>
<usage><subagent_tokens>85216</subagent_tokens><tool_uses>12</tool_uses><duration_ms>265630</duration_ms></usage>
</task-notification>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ grep -nE '^(def |@dataclass|class )' backend/mission_control/missions/selectors/dashboard.py ⏎ echo "=== return shapes ==="; grep -n 'return {' -A 12 backend/m
… [57 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
60:def pipeline_summary() -> dict:
118:def staffing_readiness() -> list[dict]:
158:def crew_utilization(window_days: int = 90) -> dict:
200:def skill_gaps() -> list[dict]:
=== return shapes ===
115:    return {"status_counts": counts, "pending_approvals": pending_approvals, "upcoming": upcoming}
116-
117-
118-def staffing_readiness() -> list[dict]:
119-    """Coverage snapshot for every currently live mission, at-risk ones first.
120-
121-    "Live" = pending_approval/approved/active and not yet
… [1,005 more chars — see the .jsonl]
```

</details>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ sed -n '140,155p;178,197p;235,250p' backend/mission_control/missions/selectors/dashboard.py`

<details><summary>⤷ Bash result</summary>

```
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

    rows.sort(key=lambda r: (not r["
… [1,268 more chars — see the .jsonl]
```

</details>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ cat >> .superpowers/sdd/00-overview/constraints.md <<'EOF' ⏎  ⏎ ## Known limitation (Task 6.1, ruled by review): dashboard readiness is O(N) in live missions ⏎
… [2,919 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
ok
```

</details>

- 🔧 **Agent** · `prompt=You are implementing Task 6.2: Dashboard API + UI. ⏎  ⏎ This is task 32 of 33 in the build of "Mission Control", a multi-tenant Django+DRF / React SPA product. Stages 1-5 are complete and verified live. Task 6.1 j
… [8,656 more chars — see the .jsonl]`

<details><summary>⤷ Agent result</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: a0d9146f1a28c35c4 (internal ID - do not mention to user. Use SendMessage with to: 'a0d9146f1a28c35c4', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do
… [580 more chars — see the .jsonl]
```

</details>

### 🤖 Assistant — 2026-08-12 08:02

**Task 6.1 done** (`fe26dd7`, review clean) — 31/33, backend at **373 tests**.

The reviewer ruled on the disclosed `1 + 3N`: it's a justified exception rather than the defect I'd warned about. The brief's own sample does the same loop, its interface names `mission_coverage` as the sole source, and no Global Constraint mandates O(1) dashboards — so the standing rule doesn't override it. Vectorising would mean re-deriving the greedy per-skill allocation that lives in the staffing selector. It's now recorded as a known limitation for the README, with a note that the real fix is a batched selector. The other three dashboard selectors are constant-query, each asserted at two data sizes.

Task 6.2 (dashboard API + UI) is running.

## 🧑 User — 2026-08-12 08:13

<task-notification>
<task-id>a0d9146f1a28c35c4</task-id>
<tool-use-id>toolu_01NyVzVS8hnxDdbgWgtRGchP</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/a0d9146f1a28c35c4.output</output-file>
<status>completed</status>
<summary>Agent "Implement Task 6.2: dashboard API + UI" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>Committed successfully. Final report is written to the report file.

- **Status:** DONE
- Commit: `a967c43` — feat: org dashboard with pipeline, readiness, utilization, skill gaps
- Tests: backend 377 passed (373 + 4 new), ruff clean; frontend 81 passed (76 + 5 new), lint/tsc clean, build succeeds
- Concerns: none outstanding — see report for the one already-known, pre-recorded limitation (staffing_readiness's 1+3N cost, unchanged, called once per request)
- Report: `/Users/samrichards/code/mission-control-mutinex/.superpowers/sdd/00-overview/task-6.2-report.md`</result>
<usage><subagent_tokens>116166</subagent_tokens><tool_uses>64</tool_uses><duration_ms>661955</duration_ms></usage>
</task-notification>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ OUT=.superpowers/sdd/00-overview/review-fe26dd7..a967c43.diff ⏎ { ⏎   echo "# Review package: fe26dd7..a967c43" ⏎   echo; echo "## Commits"; git log --oneline
… [216 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
32136 .superpowers/sdd/00-overview/review-fe26dd7..a967c43.diff
```

</details>

- 🔧 **Agent** · `prompt=You are reviewing one task's implementation: first whether it matches its requirements, then whether it is well-built. This is a task-scoped gate, not a merge review — a broad whole-branch review happens separatel
… [7,055 more chars — see the .jsonl]`

<details><summary>⤷ Agent result</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: a327dc147d464cd50 (internal ID - do not mention to user. Use SendMessage with to: 'a327dc147d464cd50', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do
… [580 more chars — see the .jsonl]
```

</details>

### 🤖 Assistant — 2026-08-12 08:14

Task 6.2 committed (`a967c43`) — backend **377**, frontend **81**, both suites and the build clean. Review running, with the misleading-zeros case as the headline check: a dashboard that renders zeros when the fetch failed is worse than a blank screen.

## 🧑 User — 2026-08-12 08:16

<task-notification>
<task-id>a327dc147d464cd50</task-id>
<tool-use-id>toolu_01Pjdxqpz19dSH8JRj1AfXcr</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/a327dc147d464cd50.output</output-file>
<status>completed</status>
<summary>Agent "Review Task 6.2 (spec + quality)" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>### Spec Compliance
✅ Spec compliant. All Interface-line requirements are met: `GET /api/v1/dashboard/` (gated on `dashboard.view`) returns `{"pipeline", "readiness", "utilization", "skill_gaps"}` from the four Task 6.1 selectors called exactly once each; four dashboard cards render per spec; `HomeRedirect` renders `&lt;DashboardPage/&gt;`; crew-member redirect unchanged.

- ⚠️ Cannot verify from diff alone: whether `mission_control/users/permissions.py`'s role→permission mapping (director/mission_lead get `dashboard.view`, crew does not) was itself reviewed/approved in an earlier task — it's pre-existing and outside this diff. I checked it directly (`backend/mission_control/users/permissions.py:41-46`) as a named-risk verification and it is correct: `_DIRECTOR` and `_LEAD` both include `Permission.DASHBOARD_VIEW`, `_CREW` does not — so all three roles land somewhere sensible (director/lead → dashboard, crew → `/my-assignments`), no dead-end.

### Strengths
- Explicit, field-by-field DRF serializers for every nested shape (`StatusCountsSerializer` spells out all 7 statuses rather than a `DictField`) — directly answers the Task 5.2-style risk. `backend/.../apis/dashboard.py:48-113`.
- `ensure_permission(request.user, Permission.DASHBOARD_VIEW)` runs before any selector call, gated on the exact catalog constant `"dashboard.view"` (verified against `permissions.py:24`). `apis/dashboard.py:117`.
- Each of the four selectors is called exactly once, inline in the response dict, no re-derivation of any dashboard number. `apis/dashboard.py:118-125`. Confirmed against `selectors/dashboard.py` that call signatures match the interface (`crew_utilization()` uses the documented default `window_days=90`).
- Frontend query branch order is exactly `isLoading → isError (role="alert") → data`, and is covered by an explicit MSW 500 test (`dashboard.test.tsx:675-682`) — the single highest-value risk named in this review is resolved and tested, not just asserted.
- Every number is labelled with what it measures ("NN% of seats filled", "org-wide utilization over the next N days", "N/min_crew min crew accepted") — `dashboard-page.tsx:444-447, 568-573`.
- Whole response zod-parsed including nested arrays (`z.array(PendingApprovalSchema)`, `z.array(ReadinessRowSchema)`, etc.), reusing the existing `MissionStatusSchema`/`MISSION_STATUSES` rather than duplicating the enum — verified those 7 values match the backend's `StatusCountsSerializer` field set (`frontend/src/features/missions/api/missions.ts:7-15`).
- No client-side recomputation of any dashboard number: `busiest`/`leastBusy` only slice/reorder the selector's already-sorted array; `coverage_pct`/`org_utilization_pct` render verbatim. `dashboard-page.tsx:479-481`.
- Empty-organisation case renders four distinct, labelled empty-state sentences rather than a wall of zeros, backed by both a backend test (`test_dashboard_api.py:198-208`) and a frontend test (`dashboard.test.tsx:690-713`).
- Backend tests cover permission-denied (403), full response shape (all nested key sets), and empty-org shape — matching the brief's exact ask plus more.

### Issues

#### Critical (Must Fix)
None.

#### Important (Should Fix)
None.

#### Minor (Nice to Have)
- `dashboard-page.tsx:480`: `leastBusy = [...crew].slice(-5).reverse()` — for organisations with ≤5 crew members, the same people appear in both "Busiest" and "Least busy" lists (just reordered). Self-disclosed by the implementer as an accepted trade-off; a `crew.length &gt; 5` guard on the "Least busy" block would remove the redundancy cheaply if it matters.
- `dashboard-page.tsx:525`: "Nothing starts in the next 30 days." hardcodes the 30-day window as UI copy, duplicating `_UPCOMING_WINDOW_DAYS = 30` in `selectors/dashboard.py` with no shared source of truth. Low risk (both are static), but if the backend window ever changes, this text silently goes stale. The API doesn't return the window value for `upcoming`, so there's no clean fix without a payload change — flagging for awareness only, not requesting a change here.
- `dashboard-page.tsx:466-468`: the loading state ("Loading dashboard…") has no `role="status"`/`aria-live`, unlike the error state's `role="alert"`. Minor accessibility polish, not requested by the brief.

### Assessment
**Task quality:** Approved
**Reasoning:** Every named risk in the review brief was checked against the diff and resolved correctly — explicit serialization, permission-gate-before-work, no recomputation or rule restatement, selectors called exactly once, correct query-branch order with a real error-state test, labelled numbers, full zod parsing, and sensible behavior for all three roles and an empty org. No critical or important defects found; the two minor items are disclosed trade-offs or cosmetic.</result>
<usage><subagent_tokens>68250</subagent_tokens><tool_uses>9</tool_uses><duration_ms>152756</duration_ms></usage>
</task-notification>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ cat >> .superpowers/sdd/00-overview/progress.md <<'EOF' ⏎ Task 6.2: complete (commits fe26dd7..a967c43, review clean, spec OK) - no fix round needed ⏎   - Ever
… [1,197 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
=== deferred minors + obligations for the README/final review ===
75
```

</details>

- 🔧 **Agent** · `prompt=You are implementing Task 6.3: Full seed, README, delivery checks. ⏎  ⏎ This is task 33 of 33 — the **final task** in the build of "Mission Control", a multi-tenant Django+DRF / React SPA product. Everything else
… [8,200 more chars — see the .jsonl]`

<details><summary>⤷ Agent result</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: a4bd960b25fed3cbf (internal ID - do not mention to user. Use SendMessage with to: 'a4bd960b25fed3cbf', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do
… [580 more chars — see the .jsonl]
```

</details>

### 🤖 Assistant — 2026-08-12 08:18

**Task 6.2 done** (`a967c43`, review clean, no fix round) — 32/33. Backend **377**, frontend **81**.

The final task is running: full demo seed, README, and delivery checks. I've told it the seed has to actually *demonstrate* the product — missions across several states, an under-staffed one so the approve guard visibly blocks, a soft conflict and a hard block so the staffing panel shows both treatments, a skill gap for the dashboard, and two tenants with enough data to prove isolation. A seed that yields an empty dashboard would be a failed deliverable regardless of row counts.

It also carries the obligation logged back at Task 1.6 (atomic, tenant-context-aware, idempotent) and an explicit requirement that the README state the known limitations honestly rather than quietly omitting them.

## 🧑 User — 2026-08-12 08:46

<task-notification>
<task-id>a4bd960b25fed3cbf</task-id>
<tool-use-id>toolu_01ANQKx9eKQ5iErcMo3LHTRe</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/a4bd960b25fed3cbf.output</output-file>
<status>completed</status>
<summary>Agent "Implement Task 6.3: seed, README, delivery" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>**Status:** DONE
Commit: `64508d9` — feat: full demo seed, README, delivery checks
Backend 385/385 passed (377 prior + 8 new RBAC-matrix), ruff clean; frontend 81/81 passed, lint/build clean; prod compose verified end-to-end from a clean DB in an isolated project (dev stack untouched).

Concerns: none blocking. One notable finding, documented in the report: the brief's sample idempotency guard (`Mission.objects_unscoped.filter(...).exists()`) both violates the "no `objects_unscoped` in application code" rule and is genuinely unsafe — the dev DB already held unrelated leftover missions under these tenant slugs from earlier tasks' gate checks, which would have made that guard silently skip seeding Meridian entirely. I replaced it with a per-tenant sentinel-mission check and cleaned the stray leftover rows (not the `pgdata` volume) as one-time housekeeping.

Report: `/Users/samrichards/code/mission-control-mutinex/.superpowers/sdd/00-overview/task-6.3-report.md`</result>
<usage><subagent_tokens>198221</subagent_tokens><tool_uses>83</tool_uses><duration_ms>1740164</duration_ms></usage>
</task-notification>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ OUT=.superpowers/sdd/00-overview/review-a967c43..64508d9.diff ⏎ { ⏎   echo "# Review package: a967c43..64508d9" ⏎   echo; echo "## Commits"; git log --oneline
… [216 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
34213 .superpowers/sdd/00-overview/review-a967c43..64508d9.diff
```

</details>

- 🔧 **Agent** · `prompt=You are reviewing one task's implementation: first whether it matches its requirements, then whether it is well-built. This is a task-scoped gate — a broad whole-branch review runs separately after this. ⏎  ⏎ This
… [7,532 more chars — see the .jsonl]`

<details><summary>⤷ Agent result</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: a2ada532f67589254 (internal ID - do not mention to user. Use SendMessage with to: 'a2ada532f67589254', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do
… [580 more chars — see the .jsonl]
```

</details>

### 🤖 Assistant — 2026-08-12 08:48

All 33 tasks are now implemented (`64508d9` — backend **385**, frontend **81**, prod compose verified from a clean database).

Notable catch on the final task: the brief's own idempotency guard used `objects_unscoped` *and* was genuinely unsafe — leftover missions from my earlier gate checks shared those tenant slugs, so it would have silently skipped seeding an entire tenant. The implementer replaced it with a per-tenant sentinel check.

Task review is running, then the whole-branch final review.

## 🧑 User — 2026-08-12 08:53

<task-notification>
<task-id>a2ada532f67589254</task-id>
<tool-use-id>toolu_01EwbZPsYgaYUNoK7D6TnKKt</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/a2ada532f67589254.output</output-file>
<status>completed</status>
<summary>Agent "Review Task 6.3 (spec + quality)" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>Good, I now have precise line references. I've completed thorough verification including independent hand-computation of the seed's crew-skill formula, mission requirement coverage, and row counts against the report's claims (all matched exactly), plus checks of `TenantManager`/`TenantModel.save()`, the tenant-context module, spec §8's FSM diagram, and the compose files referenced by the README.

### Spec Compliance
- ✅ Spec compliant. All Step 1/1b/2/3 requirements from `task-6.3-brief.md` are met, with one deliberate, correctly-reasoned, STANDING-RULE-justified divergence from the brief's own sample code (see below).

### Judgement call: replacement idempotency guard
**Ruling: correct, and the reasoning holds.** `backend/mission_control/users/management/commands/seed_demo.py:89-104` wraps `handle()` in `@transaction.atomic` (line 89), sets tenant context per tenant with `try/finally` (lines 95, 104), and gates mission-building on `Mission.objects.filter(name=spec["sentinel"]).exists()` (line 98) rather than the brief's `Mission.objects_unscoped.filter(tenant=tenant).exists()`. Verified:
- The brief's sample violates the Global Constraint (`objects_unscoped` for migrations/tests only; a management command is application code) — STANDING RULE correctly applied.
- The sentinel check is strictly safer: it only reads whether *this command's own* named mission exists (through the tenant-scoped manager, already correctly scoped by the context set on line 95), so unrelated leftover rows under the same tenant slug cannot cause a false "already seeded" skip — which the brief's coarse "any mission exists" check demonstrably would (and did, per the report).
- Partial-seed safety: because the entire command is one `@transaction.atomic` block, no interrupted/partial per-tenant state can ever be committed — either a tenant's full mission set (ending in its sentinel) exists, or none of it does. The "sentinel exists but downstream rows missing" scenario is unreachable through normal execution.
- Verified no `objects_unscoped` in application code: `grep -rn objects_unscoped backend --include=*.py` shows all hits confined to `tests/` files (permitted) plus two docstring *mentions* (not usages) in `seed_demo.py:11,14` explaining the divergence.
- The one-time dev-DB housekeeping (deleting stray leftover rows) is disclosed, doesn't touch `pgdata` beyond specific rows, and doesn't affect a fresh database (confirmed by the from-scratch prod-compose run). Not baked into the command; a documentation/process footnote, not a code defect.

### RBAC matrix: requested, not scope creep
`backend/tests/test_rbac_matrix.py` is Step 1b of the brief verbatim — brief lines 47-71 vs. diff lines 616-638 match exactly (8 URL cases × 3 roles each, one `pytest.mark.parametrize` test per URL). Confirms the "8 new tests" math (8 parametrize cases, not 24) and the fixture it depends on (`auth_client_for`) already exists at `backend/tests/conftest.py:27`.

### Dataset verification (traced relationships, not row counts)
Independently recomputed the deterministic crew-skill formula (`skills[(i+j)%8]` at `3+(i*2+j)%8`) by hand for both tenants and cross-checked against every claim in the report and README:
- **Hard block, real:** crew3 (Helios) is accepted on `Ganymede Survey` (pending, days 14–24) and accepted on `Titan Relay Deploy` (approved, days 7–20, approved *after* Ganymede staffing) — overlapping dates, accepted-on-approved → genuine hard block per `staffing.py:38,57-67`.
- **Soft conflict, real:** crew2 accepted on both `Ganymede Survey` and `Europa Ice Core`, both still `pending_approval` — overlapping dates, neither approved/active → genuine soft conflict, same roster as the hard block above.
- **Under-staffed, real:** `Ganymede Survey` requires Navigation≥5×2, Piloting≥5×1; hand-computed proficiencies for crew1/2/3 give Navigation 1/2 filled, Piloting 0/1 filled — exactly matching the report's claim and `mission_coverage()`'s greedy-by-skill matching logic (`selectors/staffing.py:193-263`). Meridian's `Vesta Mining Assessment` (Medicine≥8×2) similarly computes to 1/2 filled.
- **Skill gap, real:** `Callisto Flyby Prep` requires EVA Ops≥7×3; hand-computed EVA Ops proficiencies across all 15 Helios crew give exactly 2 qualifiers (crew3, crew11) — matches the report's claim exactly.
- **Row-count cross-check:** independently recomputed crew-skills (45/23), requirements (11/7), assignments (16/6), transitions (14/10) for Helios/Meridian purely from the seed's control flow — every number in the report's table matches exactly. This is strong evidence the report is not fabricated.
- **No hardcoded PKs:** confirmed — all lookups are by name/email/object reference.

### README verification
- All three mandated "Known limitations" items present and accurately worded (README.md:202-226), matching `constraints.md`'s canonical phrasing for the `limit: 100`/`count`-discarded truncation, the `1 + 3N` `staffing_readiness` cost, and the `Constraint "mission_dates_ordered" is violated.` example — none softened.
- Quickstart commands verified against the actual compose files: `docker-compose.dev.yml` and `docker-compose.yml` both run `migrate &amp;&amp; seed_demo` before serving, dev on :5173, prod (`SECRET_KEY=... docker compose up --build`) on :80 via the `web` service — matches README.md:48-76 exactly.
- FSM diagram (README.md:159-166) is a verbatim match of the design spec's §8 diagram.
- Design-spec link (`docs/superpowers/specs/2026-08-11-mission-control-design.md`) resolves to a real file.
- Repo-layout section matches the actual top-level directories.

### Strengths
- Exceptionally well-verified dataset: every relationship the brief demands (hard block + soft conflict together, under-staffing per tenant, org-wide skill gap, three-group my-assignments) is genuinely produced by the deterministic formula and real service calls, not asserted.
- Build-order dependency (Ganymede/Europa staffed before Titan's approval) is subtle and correctly explained both in the module docstring (`seed_demo.py:23-29`) and inline at the two call sites — good self-documentation of a real footgun.
- Correct, defensible handling of the brief's own constraint-violating sample code, with a concrete (not hypothetical) failure demonstrated and fixed.
- Idempotency test extended per brief exactly; no unrequested test changes.

### Issues

#### Critical (Must Fix)
None.

#### Important (Should Fix)
None.

#### Minor (Nice to Have)
- **Report overstates "verified by hand" for UI-level checks.** Brief Step 3 asks to "verify by hand... every list page shows data or a designed empty state; cross-role nav is correctly gated" — a UI-rendering claim. The report's evidence (task-6.3-report.md:231-264) for this is entirely `curl`/API-level (status codes, JSON payloads), not an actual browser walkthrough. API 200s are good evidence the data is there, but say nothing about frontend rendering or nav gating, which is what that line asks for. Not blocking (frontend behavior for this shape of data is already covered by earlier stages' frontend tests), but the report's phrasing ("beyond the brief's literal curl checks, to actually confirm...") oversells curl output as satisfying a manual-UI check.
- **One-time dev-DB housekeeping isn't captured in version control.** The stray-row deletion (task-6.3-report.md:74-82) was a manual Django-shell action against the shared dev database, not a script or migration. Harmless (doesn't affect fresh databases, transparently disclosed) but leaves no artifact for a future reviewer to audit if questioned later.

### Assessment
**Task quality:** Approved
**Reasoning:** The seed is genuinely atomic, tenant-correct, and idempotent (verified against `transaction.atomic`, `set_current_tenant_id`/`reset_current_tenant_id` with `finally`, and the sentinel-guard's interaction with the outer transaction); every demonstrated feature (hard block, soft conflict, under-staffing, skill gap, tenant isolation) was traced to real, correctly-computed relationships rather than taken on faith; the README's limitations section is accurate and unsoftened; and the one deliberate deviation from the brief's sample code is the right call under the STANDING RULE, backed by a concrete, reproduced failure. Only cosmetic/reporting nits found.</result>
<usage><subagent_tokens>98309</subagent_tokens><tool_uses>17</tool_uses><duration_ms>356162</duration_ms></usage>
</task-notification>

### 🤖 Assistant — 2026-08-12 08:54

All 33 tasks are complete. Building the final whole-branch review.

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ cat >> .superpowers/sdd/00-overview/progress.md <<'EOF' ⏎ Task 6.3: complete (commits a967c43..64508d9, review clean, spec OK) - no fix round needed ⏎   - Revi
… [2,168 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
745287 .superpowers/sdd/00-overview/final-review-c83bcca..64508d9.diff

 frontend/tsconfig.node.json                        |   23 +
 frontend/vite.config.ts                            |   13 +
 187 files changed, 25293 insertions(+)
```

</details>

### 🤖 Assistant — 2026-08-12 08:54

745KB is too large for a single reviewer to read meaningfully, so I'll slice the final review into focused areas run in parallel.

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ D=.superpowers/sdd/00-overview ⏎ mk(){ name=$1; shift; { echo "# FINAL REVIEW SLICE: $name (branch c83bcca..64508d9)"; echo; echo "## Files changed in this sli
… [1,146 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
core:    97748 bytes
domain:    86992 bytes
api:   176990 bytes
fe-core:    48303 bytes
fe-features:   207896 bytes
infra:    20735 bytes
```

</details>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ D=.superpowers/sdd/00-overview ⏎ # split the two oversized slices ⏎ mk(){ name=$1; shift; { echo "# FINAL REVIEW SLICE: $name (branch c83bcca..64508d9)"; echo;
… [891 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
api-src:    23365 bytes
api-tests:   153790 bytes
fe-missions:   139201 bytes
fe-rest:    68872 bytes
--- extract the deferred-minor + parked lines for the triage reviewer ---
      90 .superpowers/sdd/00-overview/final-deferred-minors.txt
```

</details>

- 🔧 **Bash** · `command=cat /Users/samrichards/.claude/plugins/cache/claude-plugins-official/superpowers/6.2.0/skills/requesting-code-review/code-reviewer.md`

<details><summary>⤷ Bash result</summary>

````
# Code Reviewer Prompt Template

Use this template when dispatching a code reviewer subagent.

**Purpose:** Review completed work against requirements and code quality standards before it cascades into more work.

```
Subagent (general-purpose):
  description: "Review code changes"
  prompt: |
    You are a Senior Code Reviewer with expertise in software architecture,
    design patterns, and best practices. Your job is to review completed work
    against its plan or requirements and identify i
… [4,700 more chars — see the .jsonl]
````

</details>

### 🤖 Assistant — 2026-08-12 08:55

Dispatching the final whole-branch review as parallel focused slices.

- 🔧 **Agent** · `prompt=You are a Senior Code Reviewer performing the **final whole-branch review** of a completed 33-task build, before merge. Your slice is the **security and tenancy core**. ⏎  ⏎ ## What was built ⏎  ⏎ "Mission Control
… [3,695 more chars — see the .jsonl]`

<details><summary>⤷ Agent result</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: afaa5ba6ae8793f9c (internal ID - do not mention to user. Use SendMessage with to: 'afaa5ba6ae8793f9c', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do
… [580 more chars — see the .jsonl]
```

</details>

- 🔧 **Agent** · `prompt=You are a Senior Code Reviewer performing the **final whole-branch review** of a completed 33-task build, before merge. Your slice is the **missions domain logic** — models, migrations, the seven-state FSM, servic
… [4,349 more chars — see the .jsonl]`

<details><summary>⤷ Agent result</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: a6b57dfb9eb810fd5 (internal ID - do not mention to user. Use SendMessage with to: 'a6b57dfb9eb810fd5', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do
… [580 more chars — see the .jsonl]
```

</details>

- 🔧 **Agent** · `prompt=You are a Senior Code Reviewer performing the **final whole-branch review** of a completed 33-task build, before merge. Your slice is the **HTTP API surface** of the missions app. ⏎  ⏎ ## What was built ⏎  ⏎ "Miss
… [3,378 more chars — see the .jsonl]`

<details><summary>⤷ Agent result</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: a437e633d2784c764 (internal ID - do not mention to user. Use SendMessage with to: 'a437e633d2784c764', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do
… [580 more chars — see the .jsonl]
```

</details>

- 🔧 **Agent** · `prompt=You are a Senior Code Reviewer performing the **final whole-branch review** of a completed 33-task build, before merge. Your slice is the **backend test suite for the missions app** — and your job is unusual: judg
… [3,240 more chars — see the .jsonl]`

<details><summary>⤷ Agent result</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: a8106cdbfc8a23be5 (internal ID - do not mention to user. Use SendMessage with to: 'a8106cdbfc8a23be5', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do
… [580 more chars — see the .jsonl]
```

</details>

- 🔧 **Agent** · `prompt=You are a Senior Code Reviewer performing the **final whole-branch review** of a completed 33-task build, before merge. Your slice is the **frontend core** — the api client, auth, app shell, router, layout and tes
… [3,547 more chars — see the .jsonl]`

<details><summary>⤷ Agent result</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: ae2eccb644ca860d4 (internal ID - do not mention to user. Use SendMessage with to: 'ae2eccb644ca860d4', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do
… [580 more chars — see the .jsonl]
```

</details>

- 🔧 **Agent** · `prompt=You are a Senior Code Reviewer performing the **final whole-branch review** of a completed 33-task build, before merge. Your slice is the **missions, matching and assignments feature UI** — the product's core scre
… [3,467 more chars — see the .jsonl]`

<details><summary>⤷ Agent result</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: aeda158835f472774 (internal ID - do not mention to user. Use SendMessage with to: 'aeda158835f472774', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do
… [580 more chars — see the .jsonl]
```

</details>

- 🔧 **Agent** · `prompt=You are a Senior Code Reviewer performing the **final whole-branch review** of a completed 33-task build, before merge. Your slice is the **remaining feature UI** — auth, crew, profile, settings, skills and dashbo
… [3,438 more chars — see the .jsonl]`

<details><summary>⤷ Agent result</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: a695bd004eace1b05 (internal ID - do not mention to user. Use SendMessage with to: 'a695bd004eace1b05', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do
… [580 more chars — see the .jsonl]
```

</details>

- 🔧 **Agent** · `prompt=You are a Senior Code Reviewer performing the **final whole-branch review** of a completed 33-task build, before merge. Your slice is the **infrastructure, CI and documentation** — the things that decide whether a
… [3,751 more chars — see the .jsonl]`

<details><summary>⤷ Agent result</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: a86df36deb65563da (internal ID - do not mention to user. Use SendMessage with to: 'a86df36deb65563da', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do
… [580 more chars — see the .jsonl]
```

</details>

- 🔧 **Agent** · `prompt=You are performing one part of the **final whole-branch review** of a completed 33-task build, before merge. Your job is not to find new issues — six other reviewers are covering the code. Your job is to **triage
… [4,117 more chars — see the .jsonl]`

<details><summary>⤷ Agent result</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: a94ffa6627f04103b (internal ID - do not mention to user. Use SendMessage with to: 'a94ffa6627f04103b', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do
… [580 more chars — see the .jsonl]
```

</details>

### 🤖 Assistant — 2026-08-12 08:58

All 33 tasks are implemented and individually reviewed. The final whole-branch review is now running as **seven parallel reviewers**, because a single 745KB diff isn't something a reviewer can actually read:

| Slice | Focus |
|---|---|
| Security core | tenancy, auth, permissions — every `User.objects` audited for tenant scoping |
| Missions domain | FSM, availability rule, matcher, migrations |
| API surface | consistency across every endpoint at once |
| Backend tests | whether the 385 tests actually discriminate, or just pass |
| Frontend core | interceptor, shared error helpers, routing |
| Feature UI ×2 | cross-feature consistency and cache coherence |
| Infra & docs | can a stranger run this; is the README honest |

Plus an eighth agent triaging the ~90 accumulated deferred findings — its most valuable job is telling me whether any of them was **mis-classified** as minor when it's actually important, with the security-adjacent ones (the director-lockout race, the user-creation TOCTOU, `tenant_update` not asserting tenant ownership) called out specifically for scrutiny.

## 🧑 User — 2026-08-12 09:01

<task-notification>
<task-id>a8106cdbfc8a23be5</task-id>
<tool-use-id>toolu_018xWGnUD1z98vnPj9fVGmHa</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/a8106cdbfc8a23be5.output</output-file>
<status>completed</status>
<summary>Agent "Final review: backend test posture" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>## Strengths

- **Real DB, real HTTP, real auth throughout.** `backend/tests/conftest.py`'s `auth_client_for` performs an actual `POST /api/v1/auth/token/` and attaches the returned JWT as a `Bearer` header — no auth mocking. Combined with `pytest.mark.django_db` and PostgreSQL-backed factories, this is genuine integration testing, not unit tests dressed up.
- **Availability date-boundary matrix is exemplary.** `test_staffing.py:2911-2937` (`OVERLAP_CASES`) enumerates 14 boundary cases including the exact pair the task called out — "touching before/after" (inclusive adjacency, `overlaps=True`) vs "one-day gap before/after" (`overlaps=False`) — applied to both `hard_blocked_user_ids` and `soft_conflicts_for_users`. This is the single sharpest test in the slice.
- **Explicit avoidance of the self-referential-constant antipattern, called out in a comment.** `test_staffing.py` (`test_status_axis_crossed_with_overlapping_dates`) parametrizes over all 7×4 `MissionStatus`×`AssignmentStatus` combinations and computes `should_hard_block`/`should_soft_conflict` from **hardcoded literals**, with an explicit comment: *"Literal, NOT HARD_BLOCK_MISSION_STATUSES: deriving the expectation from the production constant would keep all 28 cells green if the constant were widened."* `test_staffing.py:567` separately pins `HARD_BLOCK_MISSION_STATUSES == frozenset({APPROVED, ACTIVE})` against a literal, so the two tests together catch both "the constant drifted" and "the code stopped honouring the constant" without either being tautological.
- **FSM illegal-transition space is fully covered.** `test_fsm.py`'s `ILLEGAL_PAIRS` parametrization exercises every (action, from-state) pair absent from `TRANSITIONS`, asserting the real `ApplicationError` message and that no status/audit-row mutation occurred — cross-checked against literal, hand-walked legal-path tests (`test_full_lifecycle_to_completed`, `test_happy_path_submit_approve`) so the table's *content* is independently pinned, not just its complement.
- **Matcher scoring is checked against literal arithmetic, not the module's own constants.** `test_matching.py::test_score_is_the_documented_formula` and `test_soft_conflict_is_penalised_not_excluded` assert `member.score == round(1.0 * (3/9) + 0.5 * 1.0, 3)` using hardcoded `1.0`/`0.5`/`0.75`, separate from `test_weights_are_the_specified_constants` which pins the constants themselves against literals. A regression in either the weights or the formula is caught.
- **Self-approval rule is tested from both angles and the tricky edge case.** `test_fsm.py:276-310` covers "director approving own", "submitter (not creator) approving", and `test_only_the_latest_submitter_is_blocked` — after a reject→revise→resubmit cycle, only the *second* submitter is blocked, the first can review again. This is a genuinely hard case to get right and it's directly tested.
- **Real fault-injection for atomicity**, not just "assert the DB row didn't change": `test_approval_guard.py`'s `test_cancel_cascade_is_atomic_with_status_change_and_audit_row` lets the real `QuerySet.update()` execute (writing `removed` inside the open transaction) before raising, so the post-rollback assertion can only pass if the write was genuinely undone — deliberately stronger than injecting the fault before the write.
- **Deactivated-crew ruling is tested at every layer it touches**: `mission_coverage` (`test_staffing.py`, deactivation section), `staffing_validation_errors`, and the matcher's capacity/`min_crew` top-up (`test_matching.py::test_deactivated_live_member_frees_their_seat`, with `test_active_live_member_still_consumes_capacity` as its control). Good use of a positive control alongside the regression test.
- **Cross-tenant isolation** is checked on essentially every mutating and reading endpoint in this slice (assignments respond/remove/staffing, mission detail/patch/transitions/requirements, match), consistently expecting 404 per the constraint, and the matcher/dashboard/selectors additionally verify another tenant's crew/skills are invisible even when IDs collide by construction.
- **Composite-FK tests hit both sides of each FK** (`assignment_tenant_mission_fk`/`assignment_tenant_user_fk`, `requirement_tenant_mission_fk`/`requirement_tenant_skill_fk`), matching the constraints doc's explicit requirement, and correctly use `objects_unscoped` only to manufacture states the DB itself is being asked to reject — not to fake application-reachable states.
- **Query-count assertions for the four dashboard selectors and the matcher are all made at two data sizes** (`test_dashboard.py`, `test_matching.py::test_query_count_is_constant_in_roster_size`), correctly proving constancy rather than measuring a single point.

## Issues

#### Critical (Must Fix)
None found in this slice.

#### Important (Should Fix)

1. **Four "constant query count" assertions in `test_staffing.py` are single-data-point, unlike every other query-count test in this slice.** `test_soft_conflicts_is_one_query_for_many_users` (line 309, N=5 only), `test_coverage_query_count_is_constant` (line 446, one fixed shape: 3 skills/6 requirements/6 crew), `test_validation_errors_hard_block_lookup_is_not_per_member` (line 538, N=4 only), and `test_committed_assignments_is_one_query` (line 721, N=6 only) each assert a pinned query count at exactly one size. The task brief and the dashboard/matcher tests in this same slice establish the correct pattern (assert at two increasing N, e.g. `test_dashboard.py`'s `make_relevant(2)` then `make_relevant(3)` more) precisely because one measurement can't distinguish "genuinely O(1)" from "happens to be right at this N." `mission_coverage` in particular backs the O(1+3N) dashboard bound documented in the constraints file and is called from the approve guard on every approval — its only query-count regression test should be checked at two sizes, not one. **Fix:** add a second, larger-N call to `django_assert_num_queries` with the same expected count in each of these four tests, mirroring the pattern already used in `test_dashboard.py` and `test_matching.py`.

2. **No genuine concurrency test for the approve-guard row lock**, despite the spec explicitly calling for one (§14: "Approve concurrency: two competing approvals over shared crew — exactly one succeeds") and the implementation building a specific mechanism for it (`_lock_accepted_crew`'s `select_for_update`, ordered to avoid deadlock, in `mission_control/missions/services/missions.py`). The closest test, `test_approval_guard.py:69` `test_competing_approval_loses_shared_crew`, approves mission A to completion (committing the transaction) and *then* attempts to approve mission B — a purely sequential simulation. It proves the *domain outcome* (second approval sees the first one's committed hard-block) but cannot detect a missing or broken `select_for_update`: without any locking at all, sequential calls in one thread/connection would produce the identical result, since there's no actual race for the lock to prevent. A regression that dropped the lock, used the wrong queryset for it, or introduced a deadlock under real contention would pass every test in this file. This is Important rather than Critical because the *outcome* invariant is well covered — but the *mechanism* spec explicitly asked to be tested is not, which is exactly the "green tick that can't fail when the subject regresses" pattern called out in the review brief. **Fix:** add a test using two real, separate DB connections/transactions (e.g. `ThreadPoolExecutor` + `django.db.connections.close_old_connections()` per thread, or `django.test.TransactionTestCase` with two threads) that both call `transition_mission(action="approve")` for missions sharing an accepted crew member, and assert exactly one succeeds and the DB ends in a consistent state.

#### Minor (Nice to Have)

1. **`test_models.py:12`** — `TODAY = dt.date(2026, 8, 11)` is defined at module scope but never referenced anywhere in the file (dead code left over from an earlier version of the tests). Harmless but should be removed.
2. **`test_assignment_apis.py::test_bulk_propose`** asserts only `Assignment.objects_unscoped.filter(...).count() == 2`, not which two users were proposed — a bug that proposed the wrong pair of users (e.g. off-by-one in a list comprehension) would still pass. Low risk since a sibling test (`test_propose_hard_blocked_user_rejected`) does check identity elsewhere, but this specific happy-path test would benefit from asserting the actual `user_id` set.

## Recommendations

**Single most valuable missing test:** a true concurrent-approval test exercising `_lock_accepted_crew`'s `select_for_update` with two real competing transactions (see Important #2). The spec names this scenario explicitly as a required test ("exactly one succeeds"), the implementation contains code written specifically to make it safe under real contention (deterministic lock ordering to avoid deadlock, row-level locking on the shared crew), and nothing in the 385-test suite currently exercises genuine concurrency — only the sequential-outcome approximation. This is the one place where "the tests are green" and "the concurrency-safety property actually holds" could diverge without anyone noticing.

## Assessment

**Ready to merge?** With fixes

**Reasoning:** The slice is unusually strong — real HTTP/DB/auth throughout, deliberate avoidance of self-referential constant checks (with an explicit comment demonstrating the authors understood the risk), a genuinely thorough date-boundary matrix for the availability rule, and full coverage of the self-approval and deactivated-crew rulings. The two Important findings (four single-size query-count assertions, and no real concurrency test for the approve lock) are false-confidence gaps rather than wrong tests, and both are cheap to close without touching production code — neither blocks merge on its own, but both should be fixed before treating this suite's green tick as proof of the properties the spec cares about most.</result>
<usage><subagent_tokens>137891</subagent_tokens><tool_uses>28</tool_uses><duration_ms>275403</duration_ms></usage>
</task-notification>

### 🤖 Assistant — 2026-08-12 09:01

First slice back — **backend test posture: "with fixes"**. Two Important findings, both false-confidence gaps rather than wrong tests: four query-count assertions in the staffing tests measure only a single data size (so they can't distinguish genuinely constant from coincidentally-right), and there's no *real* concurrency test for the approve-guard row lock — the existing test is sequential, so dropping the `select_for_update` entirely would leave it green.

It also confirmed something good: the tests deliberately avoid deriving expectations from the production constants they're testing, with a comment showing the authors understood that trap.

Waiting on the other seven slices before I dispatch a single consolidated fix wave.

## 🧑 User — 2026-08-12 09:01

<task-notification>
<task-id>aeda158835f472774</task-id>
<tool-use-id>toolu_01DbaEFwjMpywG9qHv7Kgc2A</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/aeda158835f472774.output</output-file>
<status>completed</status>
<summary>Agent "Final review: missions/matching/assignments UI" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>## Strengths

- **Query branch order is scrupulously consistent.** Every query in this slice (`missions-page.tsx:18-25`, `mission-detail-page.tsx:14-26`, `staffing-panel.tsx:42-51`, `add-crew-dialog.tsx:73-81`, `my-assignments-page.tsx:54-63`, and `match-dialog.tsx:184-189` for the mutation-as-fetch case) follows `isLoading` → `isError` (with `role="alert"`) → data, with comments cross-referencing the sibling components that established the pattern. No query renders an empty list on a failed fetch.
- **`errorMessage`/`fieldErrorsFrom` are never re-implemented.** All nine consumers in this slice import from `src/lib/api-errors.ts` (verified via grep) — including the trickier list-shaped `items` validation errors in `requirements-editor.tsx:34-46`, which correctly unwraps the per-row shape without touching the shared helper's flat-scalar contract.
- **`hard_blocked` vs `soft_conflicts` semantics are correct everywhere they appear.** `assignments.ts:43-51` documents the distinction precisely in the schema comments; `staffing-panel.tsx:121-144` and `match-dialog.tsx:238-257` both render soft conflicts as a dismissible amber "Conflict" popover that never disables anything, and hard-blocked is a separate destructive "Unavailable" badge on the roster only (never used to gate the Remove button, and correctly absent from the matcher's `ProposedMember`, since the matching engine only ever proposes available candidates). `staffing.test.tsx:184-215` explicitly asserts both chips render independently.
- **No client-side re-derivation of server-owned numbers.** Score, breakdown, workload, coverage percentages, and `UnfilledSeat.reason` are all rendered straight from the parsed response; `match-dialog.tsx` never infers `MAX_CREW_TOO_SMALL` from `open_capacity` or vice versa (in fact `open_capacity` is parsed but not displayed at all — see Minor below).
- **Cache invalidation for the propose/remove path is correctly cross-feature-aware.** `assignments.ts:76-79`'s `invalidateStaffing` helper invalidates both the staffing key and the mission-detail key together, and is reused by both `useProposeAssignments` and `useRemoveAssignment`, so `MatchDialog`'s propose action (`match-dialog.tsx:158-169`, using `useProposeAssignments` from the assignments feature) correctly refreshes the staffing panel and mission detail it's nested inside.
- **Well-documented judgment calls.** The swap-tracking state machine in `match-dialog.tsx` (lines 28-156) carries detailed comments explaining three previously-found bugs (phantom double-proposals, stale "not proposed" markers, un-revertable swaps) and `matching.test.tsx` has dedicated regression tests for each (`re-swapping the same seat...`, `re-checking a swapped-out member...`). This is genuine evidence of iteration, not just narration.
- **Deliberate, documented schema duplication.** `matching/api/matching.ts:27-30` duplicates `SoftConflictSchema` from `assignments/api/assignments.ts` with an explicit comment explaining the bulletproof-react cross-feature-import rule that motivates it — a defensible trade-off, correctly called out rather than silently done.

## Issues

#### Critical (Must Fix)
None found.

#### Important (Should Fix)

- **Terminal-status set is triplicated with no shared export**, exactly the risk named in the brief. Three independent definitions of "mission is over":
  - `transition-buttons.tsx:38` — `const TERMINAL_STATUSES: MissionStatus[] = ["completed", "cancelled"]` (not exported)
  - `staffing-panel.tsx:19` — same array, with a comment acknowledging it's a copy because the first isn't exported
  - `my-assignments-page.tsx:28` — `const TERMINAL_MISSION_STATUSES = new Set(["completed", "cancelled"])`, a third independent copy (different container type, and doesn't even reference the other two's names)
  All three encode the same domain fact and would need to change together if the FSM's terminal set ever changed. Export one canonical `TERMINAL_MISSION_STATUSES` — `mission-status-badge.tsx` (which already owns `MISSION_STATUS_LABELS`, a natural sibling) or `missions/api/missions.ts` are the right homes — and import it in the other two files.

- **`useRespondAssignment` doesn't invalidate staffing/mission-detail caches.** `assignments.ts:137-155` invalidates only `MY_ASSIGNMENTS_KEY` on accept/decline, unlike `invalidateStaffing` (used by propose/remove) which invalidates both the staffing key and `["missions", missionId]`. Accepting or declining an assignment changes `accepted_count`, `fully_covered`, and the roster's `status` field — exactly the staffing data. In practice this is masked by React Query's default `refetchOnMount`, since `StaffingPanel` and `MyAssignmentsPage` are never mounted simultaneously in this router (each is a full route), so there's no currently-reachable path to a visibly stale panel — but it breaks the pattern the same file otherwise establishes, and would bite the moment either query gets a non-zero `staleTime` or the two views are ever composed on one page (e.g., a future "my missions" dashboard widget). Add missionId-scoped invalidation using the mission id already present on the response (`response.mission.id`).

#### Minor (Nice to Have)

- **`match-dialog.tsx` (340 lines) is the largest file in the slice** and mixes three concerns: the swap/selection state machine (lines 61-156), the propose/error handling, and ~180 lines of nested JSX for the team-member list. It's well-commented and well-tested, so it's comprehensible, but it's the clear worst offender for splitting — extracting the `selected`/`swaps` bookkeeping into a `useMatchSelection` hook and the per-member `&lt;li&gt;` block into a `MatchTeamMemberCard` component would make each piece independently testable and shrink the dialog itself to layout/wiring.
- **Inconsistent score formatting.** `match-dialog.tsx:228` formats the proposed member's own score with `.toFixed(2)`, but the swap-candidate score at line 287 (`{candidate.name} (score {candidate.score})`) is rendered raw — a floating-point breakdown value here could print with many trailing digits, unlike the consistently-rounded score elsewhere in the same dialog.
- **`open_capacity` is parsed (`matching.ts:91`) but never surfaced in the UI.** Not necessarily a bug (may be an intentional design choice outside this slice's brief), but worth confirming with whoever owns the match-dialog UX brief that dropping it silently was the intent rather than an oversight — a lead has no way to see "N seats' worth of capacity remain open" from this dialog, only per-seat reasons.
- **Field-level validation errors lack `role="alert"`.** In `mission-create-dialog.tsx` (e.g. lines 99, 109, 123...), only the aggregated `non_field_errors` block (line 171) carries `role="alert"`; the per-field messages are plain `&lt;p&gt;` tags. This is a much smaller a11y gap than the query-branch risk the brief flags (these are synchronous post-submit form errors, not a silent-empty-list-on-fetch-failure case), but still worth a pass for screen-reader users navigating a failed form.
- **`PaginatedSchema` lives in `features/skills/api/skills.ts`** and is imported cross-feature by `missions.ts`, `assignments.ts`, `crew.ts`, `settings.ts`, and `profile.ts`. This predates this slice (skills is out of scope) and is consistently applied, so it's not a defect, but it's an odd home for a genuinely global helper — `src/lib` would be the more discoverable location if it's ever touched again.

## Recommendations

1. Export a single `TERMINAL_MISSION_STATUSES` constant and replace the three local copies (Important fix above) — small, mechanical, low-risk.
2. Add mission-scoped cache invalidation to `useRespondAssignment` for defense-in-depth, even though no currently-reachable UI path exposes the staleness today.
3. Consider splitting `match-dialog.tsx` into a selection hook + list-item component on the next pass through this feature, given it's already the largest and most stateful file in the slice.
4. Confirm with product/design whether `open_capacity` was intentionally dropped from the match dialog's UI.

## Assessment

**Ready to merge?** With fixes (of the "should fix before merge, but not blocking" kind — neither Important issue is a correctness or safety defect visible to a real user today).

**Reasoning:** Domain semantics (hard-block vs. soft-conflict), the query-branch/`role="alert"` convention, the closed four-reason matching contract, and zod coverage are all correctly and consistently implemented across all three feature folders with no re-derivation of server-owned numbers. The two Important findings are real but currently-latent (masked by default refetch-on-mount and a router that never co-mounts the affected components) rather than user-visible bugs, so they're worth a quick follow-up commit rather than blocking the merge outright.</result>
<usage><subagent_tokens>110256</subagent_tokens><tool_uses>32</tool_uses><duration_ms>265278</duration_ms></usage>
</task-notification>

### 🤖 Assistant — 2026-08-12 09:01

Second slice back — **missions/matching/assignments UI: "with fixes"**. Two Important, both currently latent rather than user-visible: the terminal-status set is defined three separate times with no shared export, and `useRespondAssignment` doesn't invalidate the staffing cache (masked today only because the router never co-mounts those views).

It confirmed the domain semantics hold everywhere — hard blocks and soft conflicts rendered distinctly across all three feature folders, no client-side re-derivation of server numbers, and the shared error helpers never re-implemented.

Six slices still running.

## 🧑 User — 2026-08-12 09:03

<task-notification>
<task-id>a695bd004eace1b05</task-id>
<tool-use-id>toolu_01VXgFJShJhPMRaKrnLfyHEu</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/a695bd004eace1b05.output</output-file>
<status>completed</status>
<summary>Agent "Final review: remaining feature UI" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>Now I have all the evidence I need. Here is the final review.

### Strengths

- **Query branch order is correct everywhere in this slice.** Every list/detail screen checks `isLoading` → `isError` (with `role="alert"`) → data, so a failed fetch never renders a silent empty state: `frontend/src/features/crew/components/crew-list-page.tsx:293-302`, `crew-detail-page.tsx:241-252`, `frontend/src/features/dashboard/components/dashboard-page.tsx:503-514`, `frontend/src/features/profile/components/profile-page.tsx:843-855` (which even orders a third "draft still hydrating" check after `isError` specifically to avoid an infinite loading state — see its own comment), and all three settings tabs (`organisation-tab.tsx:1216-1223`, `skills-tab.tsx:1342-1349`, `users-tab.tsx:1562-1569`).
- **Full zod coverage, including every mutation response.** `login()`, `useSetMySkills`, `useCreateUser`/`useUpdateUser`, `useUpdateOrganisation`, `useCreateSkill`/`useUpdateSkill` all parse the server's response, not just GETs (`frontend/src/features/auth/api/auth.ts:47-51`, `frontend/src/features/profile/api/profile.ts:794-800`, `frontend/src/features/settings/api/settings.ts:1153-1195`, `frontend/src/features/skills/api/skills.ts:1782-1798`).
- **`AddUserDialog` is the model example of the CHECK-constraint pattern:** it captures `fieldErrorsFrom(err)` and renders per-field errors under name/email/password inputs while also toasting `errorMessage(err)` (`frontend/src/features/settings/components/users-tab.tsx:1449-1460`), and `settings.test.tsx:1665-1688` proves both the inline and toast paths.
- **Dashboard is well-labeled.** Every stat names what it measures and every `%` states its denominator: "`{pct}% of seats filled · {accepted}/{min_crew} min crew accepted`" (`dashboard-page.tsx:483-486`), "`{pct}% org-wide utilization over the next {N} days`" (`dashboard-page.tsx:607-611`). All four dashboard cards have distinct, sensible empty-org copy rather than bare zeros, and `dashboard.test.tsx:729-752` pins this down explicitly.
- **`PaginatedSchema` is centralized** in `frontend/src/features/skills/api/skills.ts:7-8` and reused consistently by crew, profile, settings, missions, and assignments — not duplicated per feature.
- Good tenancy-aware UX touches: profile save explicitly supports "remove every skill" as a real save-to-empty outcome rather than a no-op (`profile-page.tsx:875-889`), and a failed save leaves the draft untouched and recoverable (test at `profile.test.tsx:1069-1084`).

### Issues

#### Critical (Must Fix)
None found.

#### Important (Should Fix)

1. **`login-form.tsx` still has a private `errorMessage` copy predating `src/lib/api-errors.ts`.** `frontend/src/features/auth/components/login-form.tsx:10-15` reimplements a bare version of `errorMessage` that lacks the CHECK-constraint/`non_field_errors` fallback the shared helper now has (`frontend/src/lib/api-errors.ts:26-40`). It's the one screen in this slice not on the shared module — every other form (`organisation-tab.tsx:7`, `skills-tab.tsx:8`, `users-tab.tsx:19`, `profile-page.tsx:815`) imports it. Confirms the reported leftover. Fix: delete the local function and `import { errorMessage } from "@/lib/api-errors"`.

2. **`OrganisationTab` and `SkillsTab` never call `fieldErrorsFrom`, so a named-field validation error renders as a bare, unhighlighted "Validation error" toast.** `organisation-tab.tsx:29-36` and `skills-tab.tsx:17-25`/`31` only call `toast.error(errorMessage(err))`. `errorMessage()`'s fallback only rescues the message when the error lands under `extra.fields.__all__`/`non_field_errors` (a CHECK constraint, e.g. `Skill`'s `UniqueConstraint(Lower("name"), "tenant")` in `backend/mission_control/users/models.py:46`, which does land as `__all__` and is therefore already fine) — but a plain per-field serializer error (e.g. a future `name`-keyed validation on the tenant/skill name) would return the generic `"Validation error"` with nothing indicating which field or why, and neither tab has any field-level rendering to catch it. `users-tab.tsx`'s `AddUserDialog` in the very same file/folder already does this correctly (imports `fieldErrorsFrom`, renders `fieldErrors.email`/`name`/`password` inline) — these two tabs predate or simply didn't copy that convention. Fix: call `fieldErrorsFrom(err)` and render the relevant field's message (or `fieldErrors.non_field_errors` for the single-field organisation case) alongside the input.

3. **Settings components perform zero permission gating of their own — even though the backend enforces distinct `user.manage`, `skill.manage`, and `settings.manage` permissions separate from the page-level `settings.view` gate.** `router.tsx` gates the whole `/settings` route on `settings.view` only; none of `users-tab.tsx`, `skills-tab.tsx`, or `organisation-tab.tsx` uses `hasPermission` to conditionally show/hide the Add User dialog, role selects, skill archive/add controls, or the organisation edit pencil. This is currently harmless only because the `_DIRECTOR` role bundle happens to grant every manage permission alongside `settings.view` (`backend/mission_control/users/permissions.py`) — the only role that can reach `/settings` at all. But it means the frontend's use of the 16-permission catalog is incomplete for this slice: if `settings.manage`/`user.manage`/`skill.manage` are ever granted independently of `settings.view` (a realistic future change, since the backend already models them separately — `backend/mission_control/users/apis/settings.py:28/36/49/67/71`), a user would see fully-interactive buttons that 403 on click instead of being hidden. Not a live security bug (backend still enforces it), but a UI-permission gap worth closing with `hasPermission(user, "user.manage")` etc. around the mutating controls, consistent with how `hasPermission` is used elsewhere in the app (`app-layout.tsx:20`, `missions-page.tsx:67`, `staffing-panel.tsx:37-38`).

#### Minor (Nice to Have)

4. **Role enum duplicated verbatim in two schemas within this slice.** `z.enum(["director", "mission_lead", "crew_member"])` appears in `frontend/src/features/auth/api/auth.ts:39` and `frontend/src/features/settings/api/settings.ts:10`, plus a third independent list of the same three values with display labels in `users-tab.tsx:1422-1426` (`ROLES`). Low risk today (the role set is stable and unlikely to change), but three separate places to update in lockstep if a role is ever added/renamed. A shared `RoleSchema`/`Role` type in `src/lib` would remove the drift risk.

5. **`AddUserDialog` imports `fieldErrorsFrom` but never renders `fieldErrors.non_field_errors`,** only the three named fields (`users-tab.tsx:1480,1491,1502-1504`). If user creation ever raises a multi-field/CHECK-constraint error (nothing in `backend/mission_control/users/services.py:user_create` currently does — its only validation failure is the field-specific `email` duplicate check), it would fall back to toast-only, which is exactly the anti-pattern the constraints call out ("forms should ALSO render `fieldErrors.non_field_errors` inline rather than relying on the toast alone"). Cheap to add a generic `{fieldErrors.non_field_errors &amp;&amp; &lt;p role="alert"&gt;...}&lt;/p&gt;` block for completeness/future-proofing.

6. **`CoverageBar` (`dashboard-page.tsx:450-466`) has `role="progressbar"` with `aria-valuenow/min/max` but no `aria-label`,** so a screen-reader user tabbing directly onto the bar (rather than reading the paragraph beneath it) gets an unlabeled percentage. Adding `aria-label="Seats filled"` would close the gap; low priority since the adjacent text already explains it visually and in the accessibility tree order.

7. **`CrewUtilizationRowView`'s "Busiest"/"Least busy" split can show the same people in both lists when an org has 5 or fewer crew** (`dashboard-page.tsx:518-519`: `.slice(0,5)` and `.slice(-5).reverse()` over the same array). Correct, just redundant for small orgs — consider suppressing the "Least busy" panel when `crew.length &lt;= 5`.

8. **`profile.test.tsx`'s first test is titled "crew member edits and saves their profile" but never edits anything** (`profile.test.tsx:998-1021`) — it saves the fetched data unchanged and asserts `proficiency: 8` came from fixture data, not user interaction. Not a functional bug, just a slightly misleading test name for anyone auditing this file later.

### Recommendations

- Fix items 1 and 2 before merge — both are directly named risks from the review brief and both are trivial, mechanical changes (import the shared helper; add `fieldErrorsFrom` + inline rendering) with no behavioral risk to the passing test suite.
- Item 3 (granular permission gating in Settings) is worth a follow-up ticket rather than blocking merge — it's not exploitable under the current role model, but the inconsistency with how thoroughly `hasPermission` is used elsewhere in the app (missions, assignments, matching, nav) stands out precisely because this is a cross-feature review.
- Items 4-8 are polish; batch them into the same follow-up as item 3 if one is opened, no need for a dedicated pass.

### Assessment
**Ready to merge?** With fixes
**Reasoning:** No critical, correctness-breaking, or security-relevant bugs — query-branch ordering, zod coverage, and dashboard labeling are consistently solid across the whole slice. But the two Important items are exactly the named risks this review was asked to hunt for (the leftover private `errorMessage` in `login-form.tsx`, and two settings forms that only partially adopted the CHECK-constraint error convention that a sibling file in the same folder already gets right) — both are small, low-risk fixes and should land before merge rather than as follow-up debt.</result>
<usage><subagent_tokens>98042</subagent_tokens><tool_uses>26</tool_uses><duration_ms>315947</duration_ms></usage>
</task-notification>

### 🤖 Assistant — 2026-08-12 09:03

Third slice — **remaining feature UI: "with fixes"**. Three Important: `login-form.tsx` still carries a private `errorMessage` copy predating the shared helper (so it lacks the non-field-error fallback), two settings tabs never call `fieldErrorsFrom` while a sibling file in the same folder does it correctly, and the settings components do no granular permission gating despite the backend enforcing three distinct manage permissions.

Running tally: seven Important findings across three slices, all small and mechanical so far. Five slices still out.

## 🧑 User — 2026-08-12 09:03

<task-notification>
<task-id>a437e633d2784c764</task-id>
<tool-use-id>toolu_01FbemyeXZ6Za4TkVJ25a6Tr</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/a437e633d2784c764.output</output-file>
<status>completed</status>
<summary>Agent "Final review: API surface" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>## Strengths

- **Pagination envelope is genuinely uniform.** Both list endpoints in this slice go through the single helper: `backend/mission_control/missions/apis/missions.py:70-72` and `backend/mission_control/missions/apis/assignments.py:137-139` → `backend/mission_control/common/pagination.py:10-21`. `/me/assignments/` is paginated per controller ruling 2 despite its brief saying otherwise, and it is pinned by a test (`backend/tests/missions/test_assignment_apis.py:103`). No endpoint in the slice hand-rolls `{"results": ...}`.
- **Cross-tenant is 404 everywhere, with the permission check first.** Ten of eleven endpoints call `ensure_permission` as their first statement, before any object fetch (`apis/missions.py:65,75,93,98,121`, `apis/assignments.py:99,109,122,135,148`, `apis/matching.py:66`, `apis/dashboard.py:94`). Object access is always through a tenant-scoped manager — `selectors/missions.py:23-28` and the explicit `Assignment.objects` fetches at `apis/assignments.py:125-127,149-151` — so a foreign id is indistinguishable from a missing one. Five endpoints have explicit cross-tenant 404 tests.
- **403 vs 400 split holds across the surface.** Permission and object-level invariants raise DRF `PermissionDenied` in services (`services/missions.py:57,67`, `services/assignments.py:125`) → 403; business rules raise `ApplicationError` → 400 via `common/exception_handler.py:19-20`. The one guard written in the API layer (`apis/matching.py:69`) also uses `ApplicationError`, so it lands on the same envelope.
- **No wholesale dumps and no `ModelSerializer` anywhere.** Every field on the wire is named: `apis/missions.py:11-52`, `apis/assignments.py:44-94`, `apis/matching.py:29-61`, and the dashboard's seven nested serializers at `apis/dashboard.py:25-90`. `StatusCountsSerializer` enumerating the seven statuses instead of a `DictField` (`apis/dashboard.py:25-36`) is exactly the right instinct. No email, password, tenant id, or timestamps leak through the missions surface — user objects are reduced to `{id, name}` in every context.
- **No N+1 introduced by the view layer.** Every attribute a serializer traverses is prefetched by the selector that produced the object: `created_by.name` (`apis/missions.py:22`) against `select_related("created_by")`; `requirements__skill` / `transitions__actor` (`apis/missions.py:35,45`) against `mission_get`'s `prefetch_related`; `a.user.name` (`apis/assignments.py:65`) against `mission_assignments`' `select_related("user")`; `assignment.mission` (`apis/assignments.py:86`) against `my_assignments`' `select_related("mission")`. No selector is called inside a loop in any view; `staffing_payload` deliberately batches (`apis/assignments.py:34-42`) rather than querying per roster row.
- **One shared staffing shape for GET, propose and remove** (`apis/assignments.py:18-73`, used at `:101,:117,:130`) — the frontend parses all three with one zod schema (`frontend/src/features/assignments/api/assignments.ts:53-60`). Same discipline for `match_payload`.
- **The URL set matches spec §11 exactly** — every route in `missions/urls.py:19-31` is in the spec table, every spec row is routed, every imported view is used. No dead endpoints, no unused serializers, no orphan views in the slice.

## Issues

### Critical (Must Fix)

None.

### Important (Should Fix)

**1. `apis/matching.py:12,68-69` — a business rule decided in the view.**
```python
from mission_control.missions.services.assignments import TERMINAL
...
if mission.status in TERMINAL:
    raise ApplicationError("Cannot match a completed or cancelled mission.")
```
This is FSM legality adjudicated in the API layer, and it reaches across into another service's module constant to do it. It is the only such guard in the whole slice — the equivalent rule for propose and respond lives in the service (`services/assignments.py:32,126`). Consequence: the rule is unenforceable for any non-HTTP caller of `match_mission`, and it can't be unit-tested at the service level. Fix: add a thin `mission_match(*, actor, mission)` in `services/matching.py` (or move the guard into `match_mission` itself — it has only one caller) and reduce the view to permission → selector → service → serialize.

**2. `apis/missions.py:66-69` — the mission list is missing the spec'd date-range filter, and `search` is unreachable and undocumented.**
Spec §11 (design doc line 224) specifies `GET /missions/` filters as "status, date range, search". The view passes only `status` and `search`; there is no date filter anywhere in the request path. Separately, `search` is implemented backend-only — no UI control sends it (`frontend/src/features/missions/api/missions.ts:66` sends only `limit` and `status`; the only `search` handling in the frontend is the MSW mock at `frontend/src/testing/mocks.ts:301`). This is a gap no single task owned: the task-3.2/3.3 briefs quietly narrowed the spec's three filters to two, and the README's "Known limitations" (README.md:183-204) records neither. Fix: either add `start_date_after`/`end_date_before` params (selector + view + one test) or record both facts in the README limitations list so the spec deviation is disclosed rather than discovered.

**3. `apis/missions.py:137-140` — the only endpoint of eleven with no permission check before the object fetch.**
`MissionTransitionApi.post` fetches the mission first and delegates all permission logic to `transition_mission`. The comment explains why (the FSM table owns per-action permission), and it is correct that cross-tenant is still 404 — but it means a crew member, who holds neither `mission.view` nor `mission.progress`, gets 404 for a nonexistent mission id and 403 for a real one, i.e. an intra-tenant existence oracle over the mission id space, and it breaks the surface-wide "permission first, fetch second" shape that every other endpoint follows. Fix: add `ensure_permission(request.user, Permission.MISSION_VIEW)` as the first line — every role that can legally transition anything (lead, director) already holds it, so no behaviour changes for legitimate callers.

### Minor (Nice to Have)

**4. `apis/assignments.py:18-73` — read-composition living in the API layer.** `staffing_payload` orchestrates four selector calls (`mission_coverage`, `mission_assignments`, `soft_conflicts_for_users`, `hard_blocked_user_ids`) and assembles a composite read model. That is selector work by this codebase's own HackSoft convention; every other multi-source read shape (the dashboard's four widget groups) is composed *inside* `selectors/`. Fix: move it to `selectors/staffing.py` as `mission_staffing(mission)` and have the three views call that one selector.

**5. `apis/assignments.py:110,116,129` — redundant and over-heavy mission fetches on the staffing writes.** `mission_get` prefetches `requirements__skill` and `transitions__actor` (`selectors/missions.py:24-26`), none of which `staffing_payload` reads — it uses only `id`, `min_crew`, `max_crew`, `start_date`, `end_date`. Worse, `MissionAssignmentsBulkApi` fetches the mission twice (`:110` before the service, `:116` after) although `assignments_propose` does not modify the mission row. That's roughly three wasted queries per propose. Fix: drop the re-fetch at `:116` and pass the already-loaded `mission`.

**6. Two styles of nested output on one surface.** `apis/dashboard.py` declares nested serializers for every sub-object; `apis/missions.py:19-52`, `apis/assignments.py:44-94` and `apis/matching.py:29-61` hand-build dicts in `SerializerMethodField`s and module functions. Both enumerate their fields, so the allowlist intent is met either way, but a reader of the surface meets two conventions. Prefer the dashboard style for new nested shapes.

**7. `apis/matching.py:34-38,56` and `apis/assignments.py:53,68` — the allowlist stops one level down.** `match_payload`'s docstring claims it is "the one place the API contract is written down", but `seats`, `breakdown`, `soft_conflicts` and `candidates` are passed through as whatever dicts the engine built; likewise `filled_by` and `soft_conflicts` in `staffing_payload`. A key added to those inner dicts in `selectors/staffing.py:145-152` or the matcher does silently reach the wire — precisely the failure mode the docstring says is prevented. Today's keys are safe (ids, names, statuses), so this is about the claim, not a live leak. Fix: either enumerate the inner keys too, or soften the docstrings to say the top level is pinned.

**8. `apis/missions.py:134` vs `apis/assignments.py:144` — the same `action` field is validated two different ways.** Transitions use `CharField` (unknown action → `ApplicationError` from `services/missions.py:164`, body `{"message": "Unknown action 'x'.", "extra": {}}`); respond uses `ChoiceField` (unknown action → validation envelope `{"message": "Validation error", "extra": {"fields": {"action": [...]}}}`). Same class of client error, two body shapes. `ChoiceField(choices=list(TRANSITIONS))` on the transition input would unify them — and would make `services/missions.py:164` a defence-in-depth branch rather than the primary path.

**9. `apis/missions.py:67` — the `status` filter is unvalidated free text.** A typo'd or invalid status returns `200 {"results": [], ...}` rather than a 400, while every other client-supplied value on the surface goes through a serializer. Low impact (the UI only sends valid values), but it's the one input on the surface with no contract.

**10. `/me/assignments/` paginates a queryset with no deterministic total order.** `selectors/missions.py:50` orders by `-created_at` only, while `mission_list` at `:15` deliberately adds an `-id` tiebreak with a comment explaining why. Since bulk propose creates several assignment rows in one transaction, ties are plausible, and a tie can duplicate or drop a row across page boundaries. One-word fix in the selector (other slice — flagging it because this endpoint is the consumer).

**11. `missions/urls.py:19-31` — no `name=` on any pattern.** Consistent with `users/urls.py`, so not an inconsistency, but it means `reverse()` is unavailable and both test suites hardcode path strings; any future URL change is a grep-and-hope exercise.

## Recommendations

- Take fixes 1 and 3 before merge — both are a handful of lines and both restore a convention the rest of the surface keeps. Fix 2 is a decision (implement or disclose), not a code change, but it shouldn't ship undecided.
- Add a cross-tenant 404 test for `POST /missions/{id}/assignments/` — it's the one object-scoped write in the slice without one (staffing, respond and remove each have theirs at `tests/missions/test_assignment_apis.py:202,213,363`). The code path is safe today; the test is what keeps it that way.
- The two `bulk` write endpoints differ on empty input: `MissionRequirementsApi` accepts `items: []` (clears all requirements) while `MissionAssignmentsBulkApi` sets `allow_empty=False` (`apis/assignments.py:106`). Both are defensible, but the asymmetry is undocumented — one comment on the requirements serializer saying "empty list clears requirements, intentionally" would settle it.
- If fix 4 is taken, `staffing_payload` and `match_payload` both become pure serialization functions, at which point the API layer of this app contains nothing but permission checks, serializers and one call each — which is what the thinness rule was aiming at.

## Assessment

**Ready to merge?** With fixes

**Reasoning:** The surface is consistent where it matters most — pagination envelope, error envelope, 403/400 split, cross-tenant 404 with permission-first ordering, explicit field allowlists, and no view-layer N+1 — with no critical defects found. Three small Important items (a business rule decided in `matching.py`, the missing permission check on the transitions endpoint, and the undecided/undisclosed spec §11 filter gap) should be resolved first; everything else is polish.</result>
<usage><subagent_tokens>89906</subagent_tokens><tool_uses>30</tool_uses><duration_ms>406753</duration_ms></usage>
</task-notification>

### 🤖 Assistant — 2026-08-12 09:03

Fourth slice — **API surface: "with fixes"**. Three Important: the matcher endpoint decides FSM legality in the view (the only such guard on the surface), the transitions endpoint is the one endpoint of eleven without a permission check before the fetch (creating an intra-tenant existence oracle), and the mission list is missing the date-range filter that spec §11 specifies while its `search` filter is backend-only and undocumented.

That last one is a real spec-vs-plan gap that no single task owned — exactly what a whole-branch view is for. Four slices still running.

## 🧑 User — 2026-08-12 09:03

<task-notification>
<task-id>ae2eccb644ca860d4</task-id>
<tool-use-id>toolu_01GoJ3yDpb8kC4TYJaHM4Fkc</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/ae2eccb644ca860d4.output</output-file>
<status>completed</status>
<summary>Agent "Final review: frontend core" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>### Strengths

- **`frontend/src/lib/api-client.ts:38-59`** — the refresh-dedup design is correct and well-reasoned: `refreshPromise` is a module-level singleton checked/set synchronously (safe under JS's single-threaded model), each concurrent 401 re-reads `getRefreshToken()` fresh rather than closing over a stale value, and `.finally()` clears the promise so a *later* (non-concurrent) 401 correctly starts a new refresh using the now-rotated token. Verified by the "dedupes concurrent 401s" test (`api-client.test.ts:260-282`).
- **`frontend/src/lib/api-client.ts:369-374`** and grep confirms `localStorage`/`sessionStorage` is touched nowhere else in `src/` — the access-token-never-persisted contract holds app-wide, not just locally.
- **`frontend/src/testing/mocks.ts:1052-1074, 1075-1120`** — the requirements-PUT and transitions-POST handlers explicitly avoid mutating `missionFixture` in place (both are well-commented: "the found object may be `missionFixture` itself... mutating it directly would leak across tests"), consistently replacing the array slot with a spread copy instead. Every other mutable fixture (`initialSkills`, `initialMySkills`, `initialStaffing`, `initialMyAssignments`) returns a fresh literal per call, so `resetMockData()` genuinely isolates tests — no unreset/leaking state found.
- **`frontend/src/app/provider.tsx:29-35`** — `QueryClient` created via lazy `useState` initializer (not module scope), with a clear comment on why a singleton would leak cached auth data across renders/tests. Confirmed no cross-test leakage since every test wraps its own `&lt;AppProvider&gt;`.
- **`frontend/src/lib/api-client.test.ts`** and **`api-errors.test.ts`** drive real requests through `axios`+MSW rather than hand-constructing error shapes, so the tests exercise the actual contract, not an assumption about it.
- **`frontend/src/lib/auth.tsx:6-8, 19-21`** — `useUser`/`hasPermission` are consistently imported and reused across every feature that needs a permission check (verified via grep across `src/features`); no feature reimplements permission logic.

### Issues

#### Critical (Must Fix)
None.

#### Important (Should Fix)

1. **`frontend/src/lib/api-client.ts:72-78`** — `return api(original)` inside the `try` is not `await`ed, so if the retried request fails *after* a successful refresh (e.g. the "refreshed" access token is itself rejected, or any other error), that rejection bypasses the `catch` entirely and propagates straight to the caller. This is standard JS semantics, not a hunch — confirmed directly:
   ```
   $ node -e 'async function f(){try{return Promise.reject(new Error("boom"))}catch(e){return "caught"}}; f().catch(e=&gt;console.log("rejected:",e.message))'
   rejected: boom
   ```
   Net effect: if a retried request still 401s, the app does **not** clear tokens or redirect to `/login` (contradicting "refresh once, then log out"); it silently leaves stale-but-"refreshed" tokens in place and the user stuck with failing requests and no way out except a manual reload. This is untested (the four interceptor tests only cover: refresh success/dedup, refresh-endpoint failure, malformed refresh body — none cover "refresh succeeds but the retry still 401s"). Fix: explicitly check the retry's outcome and only force logout if it's still a 401, e.g.
   ```ts
   try {
     await refreshAccessToken(refresh);
   } catch {
     clearTokens(); window.location.assign("/login"); throw error;
   }
   try {
     return await api(original);
   } catch (retryErr) {
     if (retryErr instanceof AxiosError &amp;&amp; retryErr.response?.status === 401) {
       clearTokens(); window.location.assign("/login");
     }
     throw retryErr;
   }
   ```
   (Using a bare `return await api(original)` inside the existing single try/catch would be wrong — it would force-logout on *any* retry failure, including an unrelated 404/500.)

2. **`frontend/src/lib/api-errors.ts:596-613`** — `fieldErrorsFrom()` has no handling for the nested, index-keyed list-validation shape (`extra.fields.items: [{"skill_id":[...]}, {}]`) that list-mutation endpoints return, despite its declared return type (`Record&lt;string, string[]&gt;`) implying every value is a flat string array. This gap is real and has already produced inconsistent behaviour across features:
   - `frontend/src/features/missions/components/requirements-editor.tsx:30-46` has to build a private `rowErrorsFrom()` around the shared helper, with a comment explicitly noting `fieldErrorsFrom() only understands the flat scalar shape`.
   - `frontend/src/features/profile/components/profile-page.tsx` hits the *identical* shape (`PUT /api/v1/me/skills/` also takes an `items` array) but has no per-row handling at all (`profile-page.tsx:78-83` — only `toast.error(errorMessage(err))`). A crew member submitting an invalid proficiency will see nothing but a bare "Validation error" toast with no indication of which row is wrong, while the structurally identical mission-requirements form shows a proper inline error.
   Fix: either teach `fieldErrorsFrom`/a new `rowErrorsFrom` helper in `api-errors.ts` to handle the `items[]` shape once, and have `profile-page.tsx` adopt it, or explicitly document in `api-errors.ts` that list endpoints need their own row-level parsing and standardize that pattern's name/location so it isn't reinvented per-feature.

3. **`frontend/src/lib/auth.tsx:30-34`** — `RequirePermission` has no `isLoading` guard, and the file carries no comment recording that invariant, even though the review brief itself flags this as the second-highest risk in the slice. Today every usage is safely nested under `ProtectedRoute` (verified: all seven `RequirePermission` call sites in `frontend/src/app/router.tsx:34-89` sit inside `{ element: &lt;ProtectedRoute/&gt;, children: [{ element: &lt;AppLayout/&gt;, ... }] }`), so `useUser()`'s cache is already resolved by the time it renders. But nothing stops a future developer from using `&lt;RequirePermission&gt;` standalone (e.g. inside a modal, or a route added outside this tree) — during the loading phase `hasPermission(undefined, perm)` is `false`, so it would incorrectly bounce a permitted user away before the permission list has loaded. Fix: add a one-line comment on `RequirePermission` stating it must only be rendered under an already-resolved `ProtectedRoute`, and/or add an explicit `isLoading` no-op guard (`if (isLoading) return null;`) to make the component safe standalone as well.

4. **`frontend/src/features/auth/components/login-form.tsx:10-15`** — carries a private, drifted copy of `errorMessage()`:
   ```ts
   function errorMessage(err: unknown): string {
     if (err instanceof AxiosError &amp;&amp; typeof err.response?.data?.message === "string") {
       return err.response.data.message;
     }
     return "Something went wrong. Please try again.";
   }
   ```
   This is missing the shared helper's `"Validation error"` → `non_field_errors` fallback (`frontend/src/lib/api-errors.ts:578-594`). If the login endpoint ever surfaces a non-field validation error (rate limiting, account-lock CHECK constraint, etc.) this form will show the bare, useless "Validation error" string while every other form in the app shows the real reason. This is exactly the "private copy of these helpers" the review was asked to check for — import and use the shared `errorMessage` from `@/lib/api-errors` instead.

5. **`frontend/src/app/router.tsx:34-89`** and **`frontend/src/components/layout/app-layout.tsx:5-10`** — the route→required-permission mapping is maintained in two independent places with no shared source of truth and no compile-time type checking (plain string literals throughout, no `Permission` union). They are currently consistent (verified by direct comparison), but nothing prevents silent drift — e.g. changing `/settings`'s guard in `router.tsx` without updating the `NAV` entry (or vice versa) produces either a dead nav link or a route reachable with no visible entry point, and a typo like `"asignment.respond"` compiles fine in both places. Recommend deriving `NAV` from the same config the router builds from, or centralizing a single `ROUTE_PERMISSIONS` map consumed by both files.

#### Minor (Nice to Have)

- **`frontend/src/lib/api-client.ts:22, 41`** — `"/api/v1"` is hardcoded twice (once as `baseURL`, once in the raw refresh POST since it deliberately bypasses the `api` instance). Extract a shared constant so the two can't drift if the API prefix ever changes.
- **`frontend/src/lib/api-client.ts:36`** vs **`frontend/src/features/auth/api/auth.ts:14`** — `refreshResponseSchema` and `TokenResponseSchema` are byte-for-byte identical zod schemas (`z.object({ access: z.string(), refresh: z.string() })`) defined independently in two files. Not a bug, but worth hoisting to one shared schema so the two token-issuing code paths can't validate different shapes.
- **`frontend/src/lib/api-client.test.ts`** repeats the literal `"mc_refresh"` string rather than importing the `REFRESH_KEY` constant (which isn't exported from `api-client.ts`). Exporting it would let the test assert against the real constant instead of restating the contract's key name by hand.
- **`frontend/src/testing/mocks.ts:906-928`** — `initialStaffing()` only seeds an entry for mission id `10` (matching `missionFixture`). A test that creates a new mission (id 11+) and then navigates to its staffing panel would 404. Not currently exercised by any test (checked — no test creates-then-views-staffing), so it's latent rather than active, but worth a one-line comment noting the limitation for the next person who writes that test.

### Recommendations

- Fix the interceptor's retry-failure-after-successful-refresh path (Important #1) before merge — it's the one gap in the highest-risk file, and the fix is small.
- Delete `login-form.tsx`'s private `errorMessage` and import the shared one (Important #4) — trivial, removes a real behavioral drift.
- Decide and document a single pattern for index-keyed list-validation errors (Important #2) rather than leaving it as one bespoke `rowErrorsFrom` in `requirements-editor.tsx` and a silent gap in `profile-page.tsx`.
- Add the one-line invariant comment to `RequirePermission` (Important #3) — cheap insurance against a future misuse that today's structure happens to avoid but doesn't prevent.

### Assessment
**Ready to merge?** With fixes
**Reasoning:** The core contracts named as highest-risk (refresh-once, concurrent dedup, rotated-refresh persistence, access token never in storage) are correctly implemented and well-tested; the gaps found are edge cases (retry-after-successful-refresh not forcing logout) and consistency/documentation issues (duplicated error-message helper, undocumented `RequirePermission` invariant, incomplete nested-error-shape handling) rather than fundamental design flaws — all are small, well-scoped fixes rather than a rework.</result>
<usage><subagent_tokens>100639</subagent_tokens><tool_uses>27</tool_uses><duration_ms>396545</duration_ms></usage>
</task-notification>

### 🤖 Assistant — 2026-08-12 09:03

Fifth slice — **frontend core: "with fixes"**, and it found a genuine bug in the highest-risk file. The interceptor does `return api(original)` without `await`, so a retry that still fails bypasses the `catch` entirely: the app never clears tokens or redirects, leaving the user stuck with failing requests and no way out but a manual reload. The reviewer verified the semantics with a standalone node one-liner rather than asserting it, and noted none of the four interceptor tests cover that path.

It also found that the profile page hits the identical index-keyed list-error shape the requirements editor handles properly, but shows only a bare "Validation error" toast with no indication of which row is wrong.

Four slices left: security core, missions domain, infra, and the deferred-backlog triage.

## 🧑 User — 2026-08-12 09:04

<task-notification>
<task-id>a6b57dfb9eb810fd5</task-id>
<tool-use-id>toolu_01UiiaTr1GdrBMxUASu7xcuU</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/a6b57dfb9eb810fd5.output</output-file>
<status>completed</status>
<summary>Agent "Final review: missions domain" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>## Strengths

- **The availability rule really does live in one place.** `selectors/staffing.py:45-67` is the only expression of both the overlap test (`_overlapping`) and the `{approved, active}` set (`HARD_BLOCK_MISSION_STATUSES`). A repo-wide grep for `start_date__*`/`end_date__*` returns only `staffing.py`, the model's `end_date &gt;= start_date` CHECK, and `dashboard.py`'s single-sided "not yet ended" filters. `AssignmentStatus.ACCEPTED` appears in production code in exactly three lines: `staffing.py:62`, `staffing.py:171`, and the `assignment_respond` write. No semantic restatement anywhere — I looked for paraphrases, not just literals.
- **Soft conflicts are defined by *subtraction* from the hard block** (`staffing.py:128-138`), so the two can only drift if `_hard_block_qs` itself changes. That is the right structural choice, better than two parallel predicates.
- **`tests/missions/test_staffing.py:88-123`** cross-parametrises all 4 assignment statuses × 7 mission statuses and, deliberately, derives the expectation from *literals* rather than `HARD_BLOCK_MISSION_STATUSES` — with a comment explaining that deriving from the production constant would keep all 28 cells green if the constant were widened. That is the correct way to test a single-source rule.
- **The FSM survived four tasks intact.** `services/missions.py:34-50` is a genuine single table; `transition_mission` (157-207) runs permission → row-lock re-read → object rules → state validity → reason → guards → status write + `MissionTransition` in one `@transaction.atomic`, matching spec §8's ordering exactly. `cancel`'s assignment cascade (193-206) is inside the same transaction and is tested for atomicity (`test_approval_guard.py:146`).
- **`_lock_accepted_crew` (`services/missions.py:70-103`) is better than the spec.** Spec §8 says "row locks on affected assignments", which would not serialise anything — the competing mission's assignments are different rows. Locking the shared `User` rows, ordered by `id` to avoid the deadlock, is the correct mutex, and the docstring explains why. `test_approval_guard.py:69` proves the losing approval fails.
- **`mission_conflict_errors` (`staffing.py:266-293`) was factored out precisely so `activate` can re-run the conflicts-only check** without restating the predicate, and the docstring at `services/missions.py:120-133` reasons correctly about why the full validation must *not* re-run at activate. `test_approval_guard.py:89` and `:100` pin both halves.
- **Matcher conforms to the contract exactly.** Weights `1.0 / 0.5 / 0.75` (`matching.py:40-42`), `mean_fit = mean((prof-min)/9)` (`:113-115`, `:245`), `balance = 1 - min(days/90, 1)` (`:246`). Total ordering everywhere: `key = (-len(seats), -score, user_id)` with strict `&lt;` (`:292-294`), `ranked_bench.sort()` on a tuple ending in `user_id` (`:352`). The four reasons are module constants evaluated in the specified order (`:318-336`), and `MAX_CREW_TOO_SMALL ⇒ capacity == 0` holds by construction with no reverse inference anywhere.
- **Query discipline is asserted, not asserted-once-and-hoped.** 3 / 4 / 1 / 9 are all pinned at two data sizes (`test_staffing.py:460,557,321`; `test_matching.py:566-580`; `test_dashboard.py:138-142,345,433`). Nothing since has undone it: the matcher's three bulk fetches (`matching.py:200,206,211`) are all outside the loops, and `soft_conflicts_for_users` uses a `.values("id")` subquery rather than a round trip.
- **Migrations apply cleanly to a fresh DB in order.** `missions/0001` depends on `users/0003`, which transitively guarantees `users_user_tenant_id_uniq` (users/0001:56) and `skill_tenant_id_uniq` (users/0002:97) exist before `missions/0002` and `0004` reference them; `mission_tenant_id_uniq` is added in `0001` before `0002` uses it. All four composite FKs are `DEFERRABLE INITIALLY IMMEDIATE` with working `reverse_sql`. `makemigrations --check` reports **No changes detected** — no model/migration drift.
- **No dead code.** Every public selector, service, constant and factory in the slice has at least one production consumer; I checked all 19 exported names.

## Issues

### Critical (Must Fix)

**1. `assignment_respond` accepts without any availability check — the hard-block invariant is bypassable, and it wedges *both* missions out of activation.**
`backend/mission_control/missions/services/assignments.py:121-138`

`assignments_propose` calls `hard_blocked_user_ids` (`:64-71`), but `assignment_respond` checks only ownership, mission-not-terminal, and status-is-proposed. Nothing re-validates availability at the moment the commitment actually becomes firm.

Reachable sequence, all through supported endpoints:
1. Missions A and B overlap. Crew C is proposed on both while both are drafts (no block — neither is approved/active).
2. C accepts A; A is submitted and approved. C is now hard-blocked.
3. B is submitted and approved. This **passes** — `staffing_validation_errors` inspects only *accepted* assignments (`staffing.py:307-326`, `_accepted_assignments_qs` at `:170`), and C is merely *proposed* on B. Any other crew satisfying coverage and `min_crew` is enough.
4. C now accepts on B. No check runs. C holds accepted assignments on two overlapping **approved** missions.

Why it matters:
- It is the direct negation of §9's "first-approved wins the reservation" — the reservation A won is silently duplicated.
- `matching.py:118-132` documents as a precondition that "two accepted assignments on overlapping approved/active missions is precisely what the hard-block rule (and the approve guard that enforces it) prevents", and `_committed_days` double-counts when it is false. `dashboard.crew_utilization` (`:176-181`) double-counts identically and can report &gt;100%.
- **Both** missions are now un-activatable: `mission_conflict_errors(A)` finds C's accepted row on B (approved, overlapping), and vice versa. A — which won the reservation and "can never lose crew silently" — is blocked by a crew action taken after its approval, with the only recovery being a manual `assignment_remove`.

Note the window is unbounded even for the propose-time-checked path: any proposal outstanding when a competing mission is approved goes stale, and nothing re-checks it.

Fix (four lines, reusing the single source, no new predicate):

```python
if action == "accept":
    blocked = hard_blocked_user_ids(
        start_date=assignment.mission.start_date,
        end_date=assignment.mission.end_date,
        exclude_mission_id=assignment.mission_id,
    )
    if actor.id in blocked:
        raise ApplicationError("You are already committed to an overlapping mission.")
    assignment.status = AssignmentStatus.ACCEPTED
```

`hard_blocked_user_ids` is already imported at `:20`. Add a regression test for the four-step sequence above, plus one asserting `crew_utilization` never exceeds 100%.

### Important (Should Fix)

**2. The matcher and the propose service disagree on what consumes a `max_crew` seat.**
`backend/mission_control/missions/services/matching.py:173-178` vs `backend/mission_control/missions/services/assignments.py:73-77`

```python
# matching.py
live_user_ids = Assignment.objects.filter(
    mission=mission, status__in=LIVE_ASSIGNMENT_STATUSES, user__is_active=True
)...
capacity = max(mission.max_crew - len(live_user_ids), 0)

# assignments.py
live_count = Assignment.objects.filter(
    mission=mission, status__in=LIVE_ASSIGNMENT_STATUSES
).count()          # &lt;- no user__is_active filter
if live_count + len(users) &gt; mission.max_crew:
```

The matcher frees the seat of a deactivated live member (and its docstring at `:165-172` explicitly justifies doing so under the "deactivated crew do not fill seats" ruling); the write path still counts it. Concretely: `max_crew=3`, three live proposals of which one member was deactivated → the matcher reports `open_capacity=1` and proposes a candidate, and the lead's "propose team" click is rejected with *"This would exceed max_crew (3)."* The matcher's output is unactionable and the error names the wrong cause.

This is the ruled invariant expressed in two places, drifted. Fix by adding `user__is_active=True` to the `live_count` query in `assignments_propose` — or better, promote it to a `live_seat_count(mission)` selector in `staffing.py` alongside `_accepted_assignments_qs` and have both callers use it. Add a test with a deactivated proposed member asserting the two agree.

**3. `skill_gaps` reports total required seats as "open seats", and measures qualification against the *lowest* threshold.**
`backend/mission_control/missions/selectors/dashboard.py:209-244`

Two problems in one metric:
- `open_seats=Sum("required_count")` (`:214`) never subtracts filled seats. A fully-crewed active mission needing 3 pilots still contributes 3 "open" seats. This is the one seat-counting figure on the dashboard that does not route through `mission_coverage` — spec §13 says "open seats", and the field name promises it.
- `threshold=Min("min_proficiency")` (`:214`, applied at `:228`) counts crew who clear only the *easiest* row for that skill against a seat total that includes the hardest rows. Rows `[Pilot ≥9 ×1, Pilot ≥2 ×1]` with five crew at proficiency 2 and none at 9 reports `open_seats=2, qualified_crew=5, gap=False` — it actively hides a real gap at ≥9.

The result is a `gap` flag that both over-states demand and under-states scarcity, in opposite directions, so the sign of the error is unpredictable.

Fix: keep the single grouped query but group by `(skill_id, min_proficiency)` rather than collapsing with `Min`, so each threshold band is compared against its own qualified pool; and either subtract accepted fills (via a batched coverage helper) or rename the field to `required_seats` and label it as demand rather than open demand. Note the same batched helper would also fix the ruled-acceptable `1 + 3N` in `staffing_readiness`.

### Minor (Nice to Have)

**4. "Latest submission" is computed twice, with different tie-breaks.**
`selectors/missions.py:38-45` orders by `("-created_at", "-id")`; `selectors/dashboard.py:76-82` orders the equivalent correlated subquery by `("-created_at",)` only. Same concept, two implementations, one of which is non-deterministic on identical timestamps. Extract a shared `latest_submission_subquery()` in `selectors/missions.py`, or at minimum add `-id` to the dashboard subquery.

**5. Mixed clocks in `age_days`.**
`selectors/dashboard.py:93` subtracts `m.submitted_at.date()` (a UTC-derived date, `USE_TZ=True`, `TIME_ZONE="UTC"`) from `dt.date.today()` (the *server process* local date). On a non-UTC host these differ and `age_days` can come back `-1`. More broadly, all six `dt.date.today()` sites in the slice (`services/missions.py:150,153`; `dashboard.py:70,125,166,208`) should be `django.utils.timezone.localdate()` so the FSM's activate/complete guards use the configured project timezone rather than the container's.

**6. The live-status set is written twice in `models.py`.**
`models.py:86` defines `LIVE_ASSIGNMENT_STATUSES`; `models.py:103` hardcodes `Q(status__in=["proposed", "accepted"])` seventeen lines below it. Adding a status to the frozenset would not update the partial unique index. Use `Q(status__in=sorted(LIVE_ASSIGNMENT_STATUSES))` — deterministic, so no migration churn.

**7. A private selector is imported across modules.**
`services/missions.py:93` does `from ...selectors.staffing import _accepted_assignments_qs`. Routing through the single source is right; reaching for a `_`-prefixed name from another module is not. Promote it to a public `accepted_assignments(mission)` in `staffing.py` (it is also the natural home for the `live_seat_count` in issue 2).

**8. The `.exclude()` gymnastics in `dashboard.py` cost readability for no real safety.**
`dashboard.py:7-10, 100-102, 128-129, 211-212` write `.exclude(end_date__lt=today)` in place of `.filter(end_date__gte=today)` solely so a grep for `end_date__gte` finds only `staffing.py`. The two are exactly equivalent on non-null `DateField`s, so this defends against a grep, not against drift — and the real risk you were told to look for is the *semantic* restatement, which this does nothing about. A plain filter plus the existing module docstring would read better.

**9. `WORKLOAD_WINDOW_DAYS` does double duty and blunts the workload term.**
`matching.py:43, 206-210, 246`: it is both the ± offset (making the measured window `180 + mission_duration` days wide) and the normalising divisor (90). Anyone with ≥90 committed days across that ~6-month window scores `balance = 0`, which on a busy roster is most people, collapsing the term's discriminating power. Contract-conformant, so not a defect — but split the two constants (`WORKLOAD_WINDOW_PAD_DAYS` vs `WORKLOAD_NORMALISER_DAYS`) so the choice is visible and tunable.

**10. The roster selector doesn't surface why a deactivated member isn't counted.**
`selectors/missions.py:53-59` (`mission_assignments`) returns live assignments without filtering or flagging `is_active`, while `mission_coverage` excludes inactive users from `filled_by`/`accepted_count`. The staffing panel therefore shows a member as `accepted` who contributes nothing, with no explanation. Add `is_active` to the roster rows so the "deactivated crew don't fill seats" ruling is legible to consumers rather than just true in the aggregate.

## Recommendations

- Add a **`live_seat_count(mission)`** and a public **`accepted_assignments(mission)`** to `staffing.py`, and route `assignments_propose`, `match_mission` and `_lock_accepted_crew` through them. That closes issue 2, issue 7, and pre-empts the next drift of the same kind.
- Add a **`mission_coverage_batch(missions)`** to `staffing.py`. It is the single fix for the ruled-acceptable `1 + 3N` in `staffing_readiness` *and* for the un-subtracted seats in `skill_gaps` (issue 3). Worth doing as a follow-up even though it was outside every individual task's file list — this whole-branch view is where it becomes visible.
- Add a **cross-cutting invariant test**: for a randomly generated corpus of missions and assignments driven only through the services, assert that no user ever holds two accepted assignments on overlapping approved/active missions. That single property test would have caught issue 1, and it is the assertion `matching._committed_days` already depends on in prose.

## Assessment

**Ready to merge?** With fixes

**Reasoning:** The structural work is genuinely strong — the availability rule, the FSM table, the matcher contract and the migration ordering all hold up under a whole-branch read, and the query-count properties are pinned by tests rather than by comment. But `assignment_respond` never checks availability, which lets crew create the exact double-booking every other module is built to assume impossible and can wedge two approved missions out of activation; that plus the matcher/propose capacity drift should land before merge.</result>
<usage><subagent_tokens>103841</subagent_tokens><tool_uses>33</tool_uses><duration_ms>497514</duration_ms></usage>
</task-notification>

### 🤖 Assistant — 2026-08-12 09:04

Sixth slice — **missions domain**, and it found the most significant issue of the entire review: a **Critical**.

`assignment_respond` never checks availability. Propose checks it, approve checks it, activate re-checks conflicts — but *accept* doesn't. The reviewer traced a fully-reachable sequence through supported endpoints: crew proposed on two overlapping drafts, accepts the first, that mission gets approved, the second gets approved (legal — the crew member is only *proposed* there, and approval only inspects accepted assignments), and then they accept the second too. Now they hold accepted assignments on two overlapping approved missions — the exact state the hard-block rule exists to prevent, that the matcher documents as a precondition, and that makes utilization exceed 100%.

Worse, it wedges *both* missions out of activation, including the one that legitimately won the reservation first.

No individual task owned that gap, because each task's own guard was correct. The fix is four lines reusing the existing selector.

Two slices left, then I dispatch a single consolidated fix wave.

## 🧑 User — 2026-08-12 09:06

<task-notification>
<task-id>afaa5ba6ae8793f9c</task-id>
<tool-use-id>toolu_01NAQVjm7eTyjzrBuHsp1CCC</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/afaa5ba6ae8793f9c.output</output-file>
<status>completed</status>
<summary>Agent "Final review: security core" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>## Strengths

**The tenancy invariant holds end to end.** I audited every `User.objects` reference in application code across the whole backend (not just this slice), and all of them are correctly scoped:

| Site | Scoping |
|---|---|
| `mission_control/users/selectors.py:22` (`crew_list`) | `tenant_id=require_current_tenant_id()` — correct |
| `mission_control/users/selectors.py:35` (`user_list`) | `tenant_id=require_current_tenant_id()` — correct |
| `mission_control/users/services.py:53` (`user_create` dup check) | deliberately global; `.exists()` only, returns no cross-tenant data — correct |
| `mission_control/users/services.py:58` | `tenant=actor.tenant` — correct |
| `mission_control/users/management/commands/seed_demo.py:113` | management command, email-namespaced per tenant — acceptable |
| `missions/services/assignments.py:40` | `tenant_id=require_current_tenant_id()` — correct |
| `missions/services/missions.py:100` | `tenant_id=mission.tenant_id` — correct |
| `missions/services/matching.py:188` | `tenant_id=require_current_tenant_id()` — correct |
| `missions/selectors/dashboard.py:170` | `tenant_id=require_current_tenant_id()` — correct |

Both mutating entry points (`selectors.py:38` `user_get`, `apis/settings.py:49`) go through the scoped `user_list()`, so cross-tenant PATCH is a 404 (`tests/users/test_settings_api.py:96`). `require_current_tenant_id()` is called eagerly at queryset construction in both selectors, so it can't be silently deferred past the point where it would fail closed. **I found no cross-tenant leak in this slice.**

- `mission_control/tenants/models.py:16-18` + `middleware.py:11-15`: fail-closed manager plus a `finally`-reset context var is the right composition — the middleware resets to the pre-request value, so `TenantJWTAuthentication`'s `set_current_tenant_id` (`authentication.py:12`) can never leak into the next request on a reused worker thread. `tests/tenants/test_context.py:28-36` pins it.
- `mission_control/users/authentication.py:13` binds tenant from `user.tenant_id` (DB row), never a claim. `tests/users/test_auth_api.py:47-58` is a genuinely load-bearing test: it asserts the context is set at the authentication layer, where deleting the line would otherwise be invisible to `/auth/me/`.
- **Deactivation is airtight on both token paths.** I verified against the installed simplejwt 5.5.1: `CHECK_USER_IS_ACTIVE=True` so `JWTAuthentication.get_user` 401s a deactivated user (`authentication.py:138`), and `TokenRefreshSerializer.validate` (`serializers.py:114-124`) applies `USER_AUTHENTICATION_RULE` and refuses to mint a new access token. Rotation + blacklist are both on and confirmed live. `tests/users/test_auth_api.py:33` covers login. There is no tenant-change endpoint, so "moved user" is not reachable.
- **Permission catalog matches spec §7 exactly** — 16 values, exact strings, and all three role sets. `_DIRECTOR` is derived as `frozenset(Permission) - {ASSIGNMENT_RESPOND, OWN_SKILLS_EDIT}`, faithfully expressing spec's "everything except…". I confirmed all 16 are actually wired to a gate: 14 via `ensure_permission` call sites, plus `MISSION_PROGRESS`/`MISSION_REVIEW` through the FSM table (`missions/services/missions.py:35-47,166`). No orphan permissions.
- `tests/test_rbac_matrix.py` does what was asked: it hits real URLs with real JWTs and asserts status codes, rather than re-asserting `ROLE_PERMISSIONS`. Deleting a permission from a role set fails it.
- `common/exception_handler.py:23-24, 34-41` — reusing the DRF `Response` to preserve `WWW-Authenticate`, and promoting simplejwt's `detail` out of the dict instead of stringifying it, are both real fixes. I exercised it: `GET /api/v1/skills/` with a bad bearer returns `{"message":"Given token not valid for any token type","extra":{...}}` with no `ErrorDetail(...)` repr, and unauthenticated returns the envelope *with* the `WWW-Authenticate` header intact.
- `config/settings.py:16-20`: `SECRET_KEY` **is** genuinely mandatory outside DEBUG — verified by running settings with `DEBUG=False` and no key: `ImproperlyConfigured: Set the SECRET_KEY environment variable`.
- No `SessionMiddleware`/`CsrfViewMiddleware`/admin/staticfiles — a genuinely minimal, CSRF-surface-free JWT API. No view anywhere overrides `permission_classes` or `authentication_classes`, so the global `IsAuthenticated` default is never punctured (simplejwt's own token views carry `permission_classes = ()` themselves).
- `objects_unscoped` appears in zero application files — only tests, migrations, and the factory base. The constraint held for 33 tasks.
- Composite FKs are `DEFERRABLE INITIALLY IMMEDIATE` as ruled (`users/migrations/0003_tenant_composite_fks.py`) with working `reverse_sql`, and **both** sides are tested (`tests/users/test_tenancy.py:31,40`) with the constraint name asserted, per the Task 2.1 pattern.

## Issues

### Critical (Must Fix)
None. No cross-tenant leak, auth bypass, or privilege escalation found.

### Important (Should Fix)

**1. `backend/config/settings.py:7,10,21` — `DEBUG` and `ALLOWED_HOSTS` are fail-open, and line 7 is a dead safety net.**
Line 7 declares `environ.Env(DEBUG=(bool, False))` — the safe default — and line 10 immediately overrides it with `env("DEBUG", default=True)`. The scheme default is never consulted. I verified the live consequence: with no `.env` and no env vars, the app boots with `DEBUG=True`, `ALLOWED_HOSTS=['*']`, and `SECRET_KEY='dev-only-insecure-key-do-not-use-in-prod'`. The `SECRET_KEY` guard on line 16-20 is therefore only as strong as an operator remembering to set `DEBUG`. Any deploy path other than the shipped `docker-compose.yml` (bare gunicorn, k8s, PaaS) gets a publicly-committed signing key, Host-header wildcards, and Django's technical 500 page dumping local variables. This is exactly the class of drift a whole-branch read is for: one rule written twice, the two copies disagreeing.
*Fix:* `DEBUG = env("DEBUG")` (letting the line-7 scheme default of `False` apply), or at minimum `default=False`; and `ALLOWED_HOSTS` default `["localhost", "127.0.0.1"]`. The shipped prod compose already sets both, so nothing breaks.

**2. `backend/config/urls.py:3-6` — no `handler404`/`handler500`, so the envelope contract has holes no task owned.**
The Global Constraint is "every non-2xx response body is `{"message", "extra"}`". I ran it with `DEBUG=False`: `GET /api/v1/bogus/` returns `text/html` — `&lt;!doctype html&gt;…&lt;h1&gt;Not Found&lt;/h1&gt;` — not the envelope. Likewise `common/exception_handler.py:21` returns `None` for any non-DRF, non-`ApplicationError` exception, handing it to Django's HTML 500 page. Every routed API path is covered; every *un*routed path and every unexpected crash is not. The frontend's zod parsers and `errorMessage()` both degrade to a generic string on these, so it's not a crash, but it violates the stated contract and — under the DEBUG default in issue 1 — the 404 page enumerates the whole URLconf.
*Fix:* add `handler404` and `handler500` in `config/urls.py` returning `JsonResponse({"message": ..., "extra": {}}, status=...)`.

**3. `backend/mission_control/users/services.py:53-59` and `:8-14` — check-then-insert races 500, while the identical bug was explicitly fixed elsewhere on this branch.**
`user_create` does `User.objects.filter(email__iexact=...).exists()` then `create_user`; `skill_create` does `full_clean()` (a non-locking SELECT) then `save()`. Two concurrent requests — a double-clicked "Add user" button is enough — produce an `IntegrityError` on `users_user_email_key` / `skill_name_per_tenant_uniq`, which the exception handler does not recognise, so it becomes a 500 with no envelope. Commit `0224bcb` ("close IntegrityError-&gt;500 race in assignments_propose") solved precisely this in `missions/services/assignments.py:79-100` with an inner `atomic()` savepoint and an `except IntegrityError` that maps to an `ApplicationError`. The pattern was never back-ported to the two older services in this slice.
*Fix:* wrap the insert in the same savepoint-plus-`except IntegrityError` shape used in `assignments_propose`, re-raising as the same 400 envelope the pre-check produces.

**4. `backend/tests/test_rbac_matrix.py:8-16` — the matrix is GET-only and pins no mutating endpoint.**
The eight rows pin `mission.view`, `crew.view`, `skill.view`, `user.manage` (read), `settings.view`, `dashboard.view`, `assignment.respond` (read), `own_skills.edit` (read). Nothing in the matrix covers `mission.create`, `mission.edit`, `mission.progress`, `mission.review`, `assignment.manage`, `match.run`, `skill.manage`, or `settings.manage` at endpoint level — i.e. every permission whose misconfiguration would let a lead approve their own mission or a crew member restaff a roster. Those *are* covered by scattered per-domain tests (`tests/missions/test_mission_apis.py:165`, `test_match_api.py:32`, `test_assignment_apis.py:59`, `tests/users/test_skills_api.py:31`), so this is not a coverage hole — but the artifact that is supposed to be the single readable statement of the RBAC contract only states half of it, and a future permission-set edit that breaks writes will not fail this file.
*Fix:* extend `CASES` with `(method, url, body)` tuples for at least one write per remaining permission.

### Minor (Nice to Have)

**5. `backend/mission_control/users/permissions.py:66-71` — `HasPermission` is dead code.** Never imported anywhere in backend or tests; every call site uses `ensure_permission`. It also drags in the only `BasePermission` import. Delete it.

**6. `backend/mission_control/users/models.py:13` vs `services.py:53` — email case semantics disagree.** `BaseUserManager.normalize_email` lowercases only the *domain*, and the DB unique index is case-sensitive, but login resolves via `get_by_natural_key` with an exact `email=` match. So `user_create` correctly *refuses* a case-variant duplicate (`test_duplicate_email_case_insensitive`) yet happily stores `Bob.Smith@Acme.com` verbatim — and Bob can then only log in by reproducing that exact casing. Two places expressing "email identity" with different rules. *Fix:* lowercase the full address in `UserManager.create_user`, or add a `UniqueConstraint(Lower("email"))` and a case-insensitive auth backend.

**7. `backend/mission_control/users/permissions.py:54` — `ROLE_PERMISSIONS[role]` raises `KeyError` (→ unenveloped 500) for an unrecognised role.** Django `choices` are not DB-enforced, so any row written by a data migration or manual fix with a bad `role` 500s `/auth/me/` and every gated endpoint. `.get(role, frozenset())` would fail closed instead, matching the rest of the tenancy design's posture.

**8. `backend/mission_control/users/apis/profile.py:29` + `common/exception_handler.py:31-36` — per-item validation errors on `PUT /me/skills/` are unrenderable.** I verified the actual output for an out-of-range proficiency: `{"message":"Validation error","extra":{"fields":{"1":{"proficiency":["Ensure this value is less than or equal to 10."]}}}}`. `extra.fields` is a dict so the envelope contract is technically met, but the keys are stringified item *indices* mapping to nested dicts, not `Record&lt;string, string[]&gt;` — so `fieldErrorsFrom()` in `frontend/src/lib/api-errors.ts:46` returns a lie, `nonFieldErrorsIn` filters it to nothing, and the user gets a bare "Validation error" toast with nothing highlighted. That is precisely the failure mode the Task 3.4 ruling was written to eliminate. `tests/users/test_profile_api.py:38` asserts only `status_code == 400`, so it doesn't catch the shape. Reachable only if the UI lets a proficiency outside 1–10 through, hence Minor.

**9. `backend/mission_control/users/services.py:54-56` — the envelope literal is hand-rolled inside a service.** `ApplicationError("Validation error", extra={"fields": {...}})` duplicates the exact string and shape that `exception_handler.py:37` is the single owner of. Raising `serializers.ValidationError({"email": [...]})` produces the identical response through the one canonical path and removes a second copy of the rule.

**10. No throttling on `/api/v1/auth/token/`, and no `AUTH_PASSWORD_VALIDATORS`.** `config/settings.py` sets neither, so credential stuffing is unmetered and `"password1"` (8 chars, `apis/settings.py:22`) is an acceptable director-assigned password. The spec is silent on both, so this is a gap rather than a violation.

**11. A deactivated user's already-issued access token stays valid for up to 15 minutes**, and there is no logout/blacklist endpoint — the frontend "logout" only drops the token client-side while the refresh token remains live for its full 1-day lifetime. Inherent to stateless JWT and mitigated by the short access lifetime plus the human ruling that deactivated crew stop filling seats; recording it because the brief asked the question directly.

**12. `docker-compose.yml` runs `manage.py seed_demo` in the production stack**, creating two tenants with the hard-coded password `orbit-demo-2026` (`seed_demo.py:52`). Correct for a demo deliverable; would need gating behind an env flag for anything real.

## Recommendations

- Fix issues 1 and 2 together — they compound. A `handler500` matters much more when `DEBUG` can default on.
- Consider a `services/_atomic_insert` helper (or just a documented `except IntegrityError` recipe) so the pattern from `assignments_propose` is one thing rather than three near-copies; issue 3 exists because it was three.
- The `_DIRECTOR = frozenset(Permission) - {...}` derivation auto-grants directors any future permission. That is what spec §7 says, but pair it with the existing `len(perms) == 14` assertion in `tests/users/test_roles.py:15` — which already catches it — and note in a comment that the assertion is the intentional tripwire, not an incidental count.
- `crew_list()` filters `is_active=True`, so `GET /api/v1/crew/&lt;id&gt;/` 404s for a deactivated crew member. That is coherent with the deactivation ruling, but a staffing panel showing a historical assignment for a since-deactivated user has no way to fetch that user's detail. Worth confirming the UI never needs it.

## Assessment

**Ready to merge?** With fixes

**Reasoning:** The security core is genuinely sound — the tenancy invariant survives composition (every one of the nine `User.objects` sites is correctly scoped, `objects_unscoped` never escaped into application code, deactivation is enforced on both the access and refresh paths), and the permission catalog matches spec §7 exactly. The blockers are configuration and contract-completeness rather than authorization: fix the fail-open `DEBUG`/`ALLOWED_HOSTS` defaults (issue 1) and add `handler404`/`handler500` (issue 2) before merge; issues 3 and 4 should follow shortly after.</result>
<usage><subagent_tokens>113970</subagent_tokens><tool_uses>30</tool_uses><duration_ms>652787</duration_ms></usage>
</task-notification>

### 🤖 Assistant — 2026-08-12 09:06

Seventh slice — **security core: "with fixes"**, and importantly **no Critical**. The reviewer audited all nine `User.objects` sites in the entire backend and found every one correctly tenant-scoped; `objects_unscoped` never escaped into application code across 33 tasks; deactivation is enforced on both the access-token and refresh paths (verified against the installed simplejwt source); and the permission catalog matches spec §7 exactly.

The notable finding is a config fail-open: `settings.py` line 7 declares the safe `DEBUG=False` default and line 10 immediately overrides it with `default=True`. One rule written twice, the copies disagreeing. The reviewer booted the app to confirm — with no env vars you get `DEBUG=True`, `ALLOWED_HOSTS=['*']`, and the publicly-committed dev signing key, because the `SECRET_KEY` guard only fires when `DEBUG` is false. The shipped compose sets both, so only non-compose deploys are exposed, but that's precisely the drift a whole-branch read exists to catch.

Two slices left.

## 🧑 User — 2026-08-12 09:08

<task-notification>
<task-id>a94ffa6627f04103b</task-id>
<tool-use-id>toolu_01UzEUASRJtRXynVgb6Wzb6r</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/a94ffa6627f04103b.output</output-file>
<status>completed</status>
<summary>Agent "Final review: triage deferred minors" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>I have what I need. Here is the triage.

---

# Triage of the deferred backlog

Verified against the working tree at `master` (`64508d9`), plus live checks against the running Postgres and `manage.py check` / `makemigrations --check` (both clean). I did not re-run the full suites.

## Triage

### MUST FIX BEFORE MERGE

**1. `DEBUG` defaults to `True`, which re-opens the fail-open deploy that Task 1.5 was fixed to close.**
`backend/config/settings.py:7` and `:10`
```python
env = environ.Env(DEBUG=(bool, False))        # line 7 — declares the safe default
DEBUG = env("DEBUG", default=True)            # line 10 — overrides it
```
I read `django-environ`'s `get_value` (`.venv/.../environ/environ.py`): the scheme default is only consulted when `default is NOTSET`. It isn't. So **an unset `DEBUG` env var yields `DEBUG=True`.**

Concrete consequence: with `DEBUG` truthy, `settings.py:17-21` falls back to `SECRET_KEY = "dev-only-insecure-key-do-not-use-in-prod"` — a value committed to this repo in two places. `SIMPLE_JWT` (settings.py:62-66) sets no `SIGNING_KEY`, so SimpleJWT signs with `SECRET_KEY`. Anyone with the repo can forge an access token for any user in any tenant, and `TenantJWTAuthentication` will set the tenant context from the forged user's DB row and serve them. Plus `ALLOWED_HOSTS` defaults to `["*"]` and DRF's handler returns `None` for unexpected exceptions, so Django renders full tracebacks.

The only thing standing between this and a real breach is that `docker-compose.yml` happens to pass `DEBUG: "false"`. Any other deploy path (k8s manifest, Heroku, bare gunicorn, a second compose file) that forgets one env var gets silent, total auth bypass. The adjacent comment on lines 11-16 explicitly claims *"a deploy can never silently sign JWTs … with this well-known, publicly-committed dev value"* — the code does not deliver that. One-character fix: drop `default=True` and let the declared scheme default apply.

**2. The duplicate-skill-name error shown to users is a raw Postgres constraint name — and the README claims it isn't reachable.**
`backend/mission_control/users/models.py:46` (no `violation_error_message`), surfaced at `frontend/src/features/settings/components/skills-tab.tsx:24`.

Reproduced live against the dev DB:
```
SKILL: {'__all__': ['Constraint “skill_name_per_tenant_uniq” is violated.']}
```
A director adding a skill whose name already exists in their tenant — the single most ordinary error in the Settings → Skills tab — gets that string in a toast, curly quotes and all. There is no client-side guard and there cannot be one (the rule is case-insensitive and per-tenant, so it needs the server).

What makes this merge-blocking rather than cosmetic is `README.md:199-204`, which documents the issue but scopes it wrongly: it names only the two `CheckConstraint`s and asserts *"In practice every form validates these before submitting, so this is a defense-in-depth path, not a normal one."* That is true for `mission_dates_ordered` / `mission_crew_bounds` — `mission-create-dialog.tsx:43-54` genuinely mirrors both, and `useUpdateMission` is never wired to any UI — but it is false for the `UniqueConstraint`, which is the live path and the one the Stage 2 gate actually observed. Shipping a known user-visible defect with documentation that says it can't happen is worse than shipping it undocumented. Fix is `violation_error_message="A skill with this name already exists."` on models.py:46 (no test asserts the current text — `tests/users/test_skills_api.py:17` checks only the envelope), plus a README correction.

### SHOULD FIX SOON

**Email casing — a self-inflicted account lockout with no in-product remedy** (item 34).
`backend/mission_control/users/models.py:13` uses `BaseUserManager.normalize_email`, which lowercases *only the domain*. I proved the consequence against the live DB:
```
exact  -&gt; director@helios-aerospace.test
upper  -&gt; None
```
Login is exact-match (`ModelBackend.get_by_natural_key`). So a director who creates `Sam@example.com` produces an account that fails to authenticate for anyone typing `sam@example.com`; `user_create`'s `email__iexact` check (services.py:53) then refuses to create the lowercase variant; `user_update` (services.py:64) accepts only `role`/`is_active`, so the email cannot be corrected; there is no password-reset or email-change flow. Repair requires `manage.py shell`. One-line fix (`email.lower()`), and it also makes the create-path consistent with its own duplicate check. This is the closest thing in the list to an Important-in-disguise after the two above — I've left it here only because it needs a human to type a capital letter.

**Concurrency/ownership hardening in `users` + `tenants` services** (items 31, 32, 33) — one root cause: `mission_control/users/services.py` and `mission_control/tenants/services.py` are the only service modules that never re-read under lock or assert ownership, while `missions/services/*` do both.
- *Last-active-director race* (`services.py:64`): confirmed there is **no** guard of any kind — `grep` for `last_active|lockout` across the repo returns nothing. Sequentially safe (the `user == actor` check at :68 means the actor always survives their own write, for role changes as well as deactivation), so this is a genuine two-in-flight race only. Recovery costs SQL. The Task 2.5 reviewer explicitly ruled "acceptable, do not block; close opportunistically" — I'm not re-litigating that, just noting the fix is `transaction.atomic` + a `select_for_update` re-count.
- *TOCTOU on user create* (`services.py:53-60`): still open. Note the mitigations — `users-tab.tsx:121` disables submit on `isPending`, so the double-click path is closed client-side; only two simultaneous admins reach it, and the outcome is a 500 in logs, not corruption. Worth naming that this is the *identical* pattern that was classified **Important** in Task 4.3 and fixed there with a savepoint + `IntegrityError → ApplicationError` (`missions/services/assignments.py:8`); the two rulings are inconsistent, and copying the Task 4.3 pattern here is ~4 lines.
- *`tenant_update` asserts nothing* (`tenants/services.py:4-8`): the sole caller (`users/apis/settings.py:74-76`) always passes `request.user.tenant`, so there's no live exploit. But `Tenant` is not a `TenantModel` and has no fail-closed manager, so this is a bare cross-tenant write primitive waiting for a second caller. A one-line `if tenant.id != actor.tenant_id: raise` closes it.

**Missing negative-path tests on genuine authorization surfaces** (items 30, 12, 36) — grouped because they're the same gap.
- No permission-denied test on `PATCH /settings/users/&lt;id&gt;/`. The guard *is* present and correct (`apis/settings.py:49`, before `user_get`, so a lead gets 403 not 404), and `_DIRECTOR`/`_LEAD` in `permissions.py:31-44` confirm `USER_MANAGE` is director-only. But `tests/test_rbac_matrix.py` only exercises `GET`, and `test_lead_cannot_manage_users` is a `GET`. This is the role-assignment escalation surface and the cheapest test outstanding.
- No test for an expired token or the `/auth/token/refresh/` endpoint (`tests/users/test_auth_api.py` covers invalid-bearer, no-credentials, inactive-user).
- Nothing pins the deactivation-lockout guarantee, which rests entirely on two SimpleJWT defaults.

**Stale docstring that actively contradicts the code it describes** (item 72).
`backend/mission_control/missions/selectors/staffing.py:301-302` still says coverage/crew-bounds *"cannot regress between approval and activation without going through `assignment_remove`"*. That was corrected in `services/missions.py:120-133` (deactivating a crew member also regresses coverage, per the Task 4.2 ruling) but never here. A future dev reading `staffing.py` to decide whether the activate guard can be tightened will reach the wrong conclusion. One line.

**Cheap, real test gaps** (items 24, 28, 29, 53, 54, 55, 61, 73, 74, 78, 80): no test for `skill_name_per_tenant_uniq` / `crewskill_user_skill_uniq`; no test for `crew_list()`'s `is_active` filter or `/api/v1/crew/`'s envelope; no test that a `MISSION_LEAD` gets 403 on approve; no API-level test that a staffing failure yields the 400 envelope; frontend transition clicks untested. Each individually trivial; see Patterns.

**Duplication that has already forked once** (items 20, 37, 81, 82, 87): `TokenResponseSchema` vs `refreshResponseSchema`; `login-form.tsx:10`'s private `errorMessage` copy predating `lib/api-errors.ts`; `user__is_active=True` in both `matching.py:175/189` and `staffing.py:171`; `SoftConflictSchema` in two feature modules; `_UPCOMING_WINDOW_DAYS = 30` duplicated in UI copy (the backend never puts it on the wire — `apis/dashboard.py`'s `UpcomingMissionSerializer` omits it, unlike `UtilizationSerializer.window_days`).

**Documentation of the tenancy footguns** (items 1, 4): `TenantModel` (`tenants/models.py:20-33`) has no docstring at all — neither the "`objects_unscoped` is migrations/tests only" rule nor the "bulk_create bypasses stamping" trap is recorded at the class. Both rules *are* in `constraints.md`, which will not travel with the code.

### ACCEPT AS-IS

- **2** middleware exception path untested — the `finally` at `middleware.py:14-15` is trivially correct.
- **3** `TenantModel.save()` doesn't assert the stored row's tenant — every coherence rule is a composite FK; this is redundant.
- **5** conftest `try/finally` — pytest resumes a yield-fixture generator regardless of test outcome; no live gap.
- **8** `users/urls.py` outside the brief's file list — justified, restores `manage.py check`.
- **9** pagination boundary cases — DRF's own `LimitOffsetPagination`.
- **17, 18** CI caching; `.dockerignore` missing `*.sqlite3` — CI speed only; the project is Postgres-only.
- **21, 22** `testing/server.ts` shim; 8 `only-export-components` lint warnings (I ran `npm run lint` — exit 0, all warnings).
- **23** `SkillFactory` tenant footgun — documented verbatim in `constraints.md:91-94`.
- **25, 26** no index on composite-FK referencing columns; redundant `&gt;= 0` CHECK from `PositiveSmallIntegerField`.
- **27** `crew_skills_set` bulk_create bypasses `full_clean` — `apis/profile.py:12` validates `proficiency` 1..10 at the serializer, so the CHECK is unreachable.
- **35** empty PATCH body is a 200 no-op — harmless.
- **38, 57, 58** unscoped `screen.findByText` in three tests.
- **39** no success toast on user create.
- **40, 41** `useSetMySkills` invalidation scope; `draft` seeding not re-syncing on background refetch.
- **43** LIST inputs key `extra.fields` by index — **handled**: `requirements-editor.tsx:32` documents it and parses the list shape itself.
- **44, 68, 69** no `Meta.indexes` on Mission; `assignment_live_uniq` hardcodes the status list (deriving from a `frozenset` would make migration output non-deterministic — the literal is arguably correct); `Assignment.status` has no `db_index`.
- **48, 49, 50, 51, 52** FSM nits. Note **51** is unreachable: there is no mission-delete endpoint, and the API 404s via `mission_get` first.
- **56** `MissionDetailApi.InputSerializer` `required=False` — correct with `partial=True`.
- **59** MSW `cancel` omits `rejected` — confirmed at `mocks.ts:399`; mock-fidelity only.
- **60, 62** no UI ownership gating (server fails closed); `useSkills()` fetched unconditionally.
- **63-66** exception-handler edge cases; **63** was fixed at the time and the `__all__`/`non_field_errors` merge is live in `api-errors.ts:18-25`.
- **70, 71, 76** `staffing_payload` in `apis/`; redundant prefetch and double `mission_get`; parsed-then-discarded mutation responses.
- **75** progress-bar aria — partially fixed already (`dashboard-page.tsx:14-16` has valuemin/max; `staffing-panel.tsx:83` doesn't). ARIA defaults are 0/100, so this is cosmetic.
- **77, 79, 88** no explicit Cancel in the decline dialog; raw ISO dates at `my-assignments-page.tsx:37`; dashboard loading state has no `role="status"` (`dashboard-page.tsx:66`; the error state at :70 does).
- **83** `open_capacity` parsed but unrendered.
- **84, 86** the 1+3N wording; small-org overlap between "Busiest" and "Least utilised".
- **85** `org_utilization_pct` double-rounds (`dashboard.py:194-196`) — max error ~0.5pp on an integer percentage.
- **89, 90** report-evidence and manual-cleanup process notes; nothing in the tree to change.
- **Rulings I did not revisit**, per instruction: UI pagination out of scope; `1 + 3N` dashboard; `actor` kwarg convention; soft-conflict closed list; `DEFERRABLE INITIALLY IMMEDIATE`; `/me/assignments/` pagination.

### ALREADY FIXED / NOT REPRODUCIBLE

- **10 + 11** `bare except ImportError` and the `TODO(Task 1.5)` fallback branch — `common/exception_handler.py:6` is now a plain `from rest_framework.views import exception_handler as _drf_exception_handler`. No `try`, no TODO.
- **6** OBLIGATION → 2.1, DB-level cross-tenant tests — discharged: `tests/users/test_tenancy.py` has 6 tests including both sides of both composite FKs (`crewskill_tenant_user_fk`, `crewskill_tenant_skill_fk`) and the fail-closed manager.
- **7** OBLIGATION → 1.3, `manage.py check` green — ran it: *"System check identified no issues (0 silenced)"*; `makemigrations --check` reports *"No changes detected"*.
- **13** OBLIGATION → 1.8/1.9, rotated refresh persisted — `api-client.ts:47-51` parses and writes both tokens back, with a single-flight promise at :34 so concurrent 401s can't blacklist each other.
- **15 + 16** `seed_demo.handle()` unwrapped — now `@transaction.atomic` at `seed_demo.py:87`, with tenant context set/reset around every `TenantModel` write.
- **19** `src/App.tsx` / `src/App.css` — both deleted.
- **45** OBLIGATION → 3.3, `KeyError` on missing requirement keys — discharged: `apis/missions.py:107-113`, all three fields DRF-required, with a comment saying why.
- **46** OBLIGATION → 4.4, activate guard scope — decided deliberately: `services/missions.py:120-140` runs conflicts-only `mission_conflict_errors`, approve runs the full validation, and the split is pinned by a test.
- **47** OBLIGATION → 4.4, cancel flips live assignments to `removed` — built at `services/missions.py:193-206`, inside the same atomic block as the status write and audit row.
- **67** OBLIGATION → 4.4, cascade-delete untested — discharged per the Task 4.4 ledger; composite FKs confirmed present in `migrations/0004_assignment_composite_fks.py`.

---

## Patterns

**One systemic finding: no model constraint in the codebase sets `violation_error_message`.** `grep` across `mission_control/` returns zero. Every `CheckConstraint` and `UniqueConstraint` — `mission_dates_ordered`, `mission_crew_bounds`, `skill_name_per_tenant_uniq`, `crewskill_proficiency_1_10`, `requirement_proficiency_1_10`, `requirement_count_gte_1`, `assignment_live_uniq` — falls back to Django's `"Constraint “%(name)s” is violated."` These land in `extra.fields.__all__`, which `api-errors.ts` faithfully normalises and every form dutifully renders. The frontend plumbing for non-field errors was built well (Task 3.4, and it's a `constraints.md` rule); the backend simply never supplied a human sentence for it to carry. Today most paths are masked by client-side echoes; each new form or each removed echo un-masks another. Fix the class, not the two instances the README names.

**Second pattern: the deferred *tests* cluster hard on negative paths, and specifically on authorization.** Of ~30 test-gap items, the ones that matter are all "we tested that the allowed thing works, not that the forbidden thing fails" — PATCH permission denial, lead-approves-403, expired tokens, deactivation lockout, `is_active` filtering, staffing-failure envelopes. 385 tests is a lot of green, and the green is concentrated on happy paths. Not merge-blocking; worth one deliberate session.

**Third, minor: five instances of "the same fact stated in two places"** (items 20, 37, 81, 82, 87) plus two undocumented traps (1, 4). Individually trivial. Collectively they say the codebase leans on `constraints.md` to carry knowledge that should live in docstrings — and `constraints.md` is an SDD artifact that won't survive the merge into the code's own reading path.

**Note on the list itself:** `final-deferred-minors.txt` filters out the seven ledger entries tagged *plan-mandated* / *plan decision*. That filter is defensible, but one of them is tenancy-relevant — Task 3.1's "`MissionTransition` has no composite tenant FK". I checked it: `migrations/0002` adds composite FKs for `MissionRequirement` only, and `MissionTransition` has none. It is not exploitable (`transition_mission` sources `mission` from the tenant-scoped `mission_get` and `actor` from `request.user`) and `constraints.md:8` doesn't list `MissionTransition` among the models requiring one, so it's spec-compliant. Flagging only so the controller knows the list isn't the complete ledger.

## The one that matters most

**Item 34, `normalize_email` lowercasing only the domain** (`backend/mission_control/users/models.py:13`).

Everything else in this backlog degrades gracefully. This one manufactures an account that cannot be used and cannot be repaired through the product: login is exact-match (proven above), the `iexact` duplicate check blocks re-creating the correct-cased address, `user_update` has no `email` parameter, and there's no password-reset or email-change flow anywhere. The first month of real use is exactly when directors are hand-entering their crew roster into a fresh tenant — the highest-density window for someone to type a capital letter. The support path is `manage.py shell` on production. One line to fix, and it removes a live inconsistency with the duplicate check sitting eleven lines away in `services.py:53`.

Runner-up by probability, not by damage: item 42 (the raw constraint text), which is closer to certain but only costs credibility.

## Mis-classified

**Yes — one clear case, one arguable.**

**Clear: item 14, the `DEBUG` default, is Important, not minor.** It was logged as *"inconsistent, predates this task"* — a style observation. In the very same task (1.5), the review had raised **Important**: *"weak+published SECRET_KEY default = InsecureKeyLengthWarning + fail-open deploy"*, and it was fixed by making `SECRET_KEY` mandatory when `DEBUG` is falsy. The minor logged three lines later in the ledger is precisely the condition that decides whether that fix ever engages. `DEBUG` unset → `DEBUG=True` → the Important finding is un-fixed. The reviewer saw both facts in one sitting and filed them at different severities because one was framed as a duplicate-default inconsistency rather than as "the guard's predicate defaults the wrong way." Evidence: `settings.py:7,10,17-21`, `django-environ`'s `get_value` skipping the scheme default whenever an explicit `default=` is passed, and `SIMPLE_JWT` (`:62-66`) carrying no `SIGNING_KEY`.

**Arguable: item 32, the user-create TOCTOU, is inconsistent with a ruling already made elsewhere.** The identical pattern — pre-check, then a write that can lose a race and raise `IntegrityError` → unhandled 500 — was rated **Important** in Task 4.3 for `assignments_propose` and fixed with a savepoint plus `IntegrityError → ApplicationError`. In Task 2.5 the same shape in `user_create` was rated minor. The client-side `isPending` guard in `users-tab.tsx` makes the practical exposure genuinely lower, so I'd not promote it to merge-blocking — but the two tasks applied different bars to the same bug, and the cheap resolution is to copy the Task 4.3 pattern.

**Not mis-classified, on inspection:**
- *Last-active-director race* — correctly minor. I confirmed there is no sequential path: `user == actor` (services.py:68) blocks self-modification for both `role` and `is_active`, so the acting director always survives their own write. Concurrency-only, and the Task 2.5 reviewer ruled it explicitly.
- *`tenant_update` ownership* — correctly minor **today**: one caller, and it passes `request.user.tenant`. It's a latent primitive, not a live hole.
- *Developer-facing constraint messages* — correctly minor **as a class**, but the specific `skill_name_per_tenant_uniq` instance was under-scoped (see MUST FIX #2): the README asserts it's unreachable when it is the normal path.

## Assessment

**Does the deferred backlog block merge?** Yes — narrowly.

**Reasoning:** Two items shouldn't ship: the `DEBUG` default silently re-opens the fail-open deploy that a prior Important finding was fixed to close (any deploy path other than the shipped compose file signs JWTs with a key committed to this repo), and the duplicate-skill-name error puts a raw Postgres constraint name in front of users on a normal path that the README claims is unreachable. Both are one-line code changes plus a README correction; the remaining ~85 items are correctly-judged minors or already discharged, and none of them justify holding the branch.</result>
<usage><subagent_tokens>138723</subagent_tokens><tool_uses>68</tool_uses><duration_ms>603743</duration_ms></usage>
</task-notification>

### 🤖 Assistant — 2026-08-12 09:09

Eighth slice — **the deferred-backlog triage**, and it did exactly what I hoped: found a **mis-classification**.

Back at Task 1.5, a review rated "weak, published `SECRET_KEY` default = fail-open deploy" as Important and it was fixed by making `SECRET_KEY` mandatory when `DEBUG` is false. Three lines later in the same ledger, the `DEBUG` default inconsistency was logged as a *minor* style note. But that minor **is the predicate that decides whether the Important fix ever engages** — `DEBUG` unset means `DEBUG=True` means the guard never fires. Same reviewer, same sitting, two severities, because one was framed as a duplicate-default inconsistency rather than as the guard's condition defaulting the wrong way. It independently confirms the security slice's finding.

It also found the README actively wrong: it documents the raw-constraint-text issue but claims every form validates first, so it can't happen in practice. That's true for the two CHECK constraints named — and false for the duplicate-skill-name unique constraint, which is the *normal* path in Settings → Skills and which my own Stage 2 gate observed live. Shipping a known user-visible defect with docs saying it's unreachable is worse than shipping it undocumented.

Systemic finding behind both: **no model constraint anywhere in the codebase sets `violation_error_message`** — the frontend plumbing for non-field errors was built well, the backend just never supplied a human sentence for it to carry.

It also verified ~11 backlog items as already fixed, and named the highest-future-risk item: `normalize_email` lowercases only the domain, so a director typing a capital letter creates an account that can't log in and can't be repaired through the product.

One slice left.

## 🧑 User — 2026-08-12 09:09

<task-notification>
<task-id>a86df36deb65563da</task-id>
<tool-use-id>toolu_01TmjM9NMHVgxXsQkAaJ45xf</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/a86df36deb65563da.output</output-file>
<status>completed</status>
<summary>Agent "Final review: infra, CI and docs" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result># Infrastructure, CI, and Documentation Review — Mission Control

Scope: `.env.example`, `.github/workflows/ci.yml`, `README.md`, `backend/.dockerignore`, `backend/Dockerfile`, `backend/pyproject.toml`, `docker-compose.dev.yml`, `docker-compose.yml`, `frontend/.dockerignore`, `frontend/Dockerfile`, `frontend/nginx.conf`, `frontend/package.json`. Verified against `constraints.md` and by running the quickstart commands, building the backend image, and running both test suites, ruff, oxlint, and the frontend build.

### Strengths

- **`.env.example:29-32` / `docker-compose.yml:13`** — `SECRET_KEY` genuinely fails closed via `${SECRET_KEY:?set SECRET_KEY}`, backed by a second layer in `backend/config/settings.py:16-20` (`DEBUG=False` path has no default, raises `ImproperlyConfigured`). Verified: `docker compose up` with no `SECRET_KEY` set refuses to interpolate.
- **Test-count and lint claims verified true.** Ran the actual suites: backend `uv run pytest -q` → 385 dots/385 tests, `uv run ruff check .` → "All checks passed!"; frontend `vitest run` → "81 passed (81)", `npm run lint` exits 0, `npm run build` succeeds (`tsc -b &amp;&amp; vite build`). The build/test claims in the prompt are not just asserted, they're true.
- **README known-limitations section (`README.md:183-201`) is accurate and specific, not softened.** Cross-checked all three against code:
  - Pagination: frontend list hooks do use `limit: 100` and discard `count` (matches the controller ruling verbatim).
  - `1 + 3N` dashboard cost: `staffing_readiness()` correctly named at `backend/mission_control/missions/selectors/dashboard.py`.
  - CHECK constraints: `mission_dates_ordered` and `mission_crew_bounds` (`backend/mission_control/missions/models.py:33,37`) do lack `violation_error_message`, exactly as described.
- **Demo credentials table (`README.md:100-116`) matches `seed_demo.py` exactly** — same emails, same password (`orbit-demo-2026` = `DEMO_PASSWORD`), same tenant slugs, same crew counts (15/8). The "interesting crew1 login" and the soft-conflict/hard-block demo-tour narrative (`README.md:127-140`) match the seed script's actual assignment states (Ganymede crew2 soft conflict with Europa, crew3 hard-blocked by the later-approved Titan) precisely.
- **Tenancy and dependency-direction claims are true.** Grepped `common/`, `tenants/` for imports of downstream apps — none found, confirming the one-way `missions → users → tenants → common` dependency graph the README describes.
- **`nginx.conf` and Vite dev proxy are consistent with the backend's actual URL prefix.** `proxy_pass http://backend:8000` (no trailing slash) preserves `/api/v1/...`, matching `config/urls.py`'s `path("api/v1/", ...)`, and `vite.config.ts`'s proxy target reads `VITE_PROXY_TARGET`, matching `docker-compose.dev.yml:29`.
- **`.dockerignore` files are correct and minimal for their stated purpose** — both exclude the platform-specific artifact directories (`.venv/`, `node_modules/`) that would otherwise corrupt a `COPY . .` build, per `backend/.dockerignore:1` and `frontend/.dockerignore:1`.
- **No secrets committed.** `.env.example` ships only an empty `SECRET_KEY=` placeholder; dev Postgres credentials (`mission`/`mission`) are throwaway dev-only values, not exposed on a host port in the prod compose.

### Issues

#### Critical (Must Fix)

- **`docker-compose.yml:9` and `backend/Dockerfile:5` — the "prod" container installs dev/test dependencies over the network on every single start, defeating the multi-stage `--no-dev` build.** The Dockerfile correctly does `RUN uv sync --frozen --no-dev` (line 5), producing an image whose `.venv` excludes `pytest`/`pytest-django`/`factory-boy`/`ruff`. But the compose command is `sh -c "uv run python manage.py migrate &amp;&amp; uv run python manage.py seed_demo &amp;&amp; uv run gunicorn config.wsgi --bind 0.0.0.0:8000"` — none of these three `uv run` invocations pass `--no-dev` (or `--frozen`), and plain `uv run` performs an implicit sync that installs the `dev` dependency group by default (confirmed via `uv run --help`: `--no-dev` "Disable the development dependency group", on by default otherwise).
  I reproduced this directly against the real image: built `backend/Dockerfile` and ran `docker run --rm &lt;image&gt; uv run gunicorn --version`. Output:
  ```
  Downloading pygments (1.2MiB)
  Downloading faker (2.0MiB)
  Downloading ruff (10.5MiB)
  Installed 8 packages in 69ms
  gunicorn (version 26.0.0)
  ```
  Every container start (a) requires network egress to PyPI just to boot — a prod deployment behind an egress-restricted network fails to start entirely — and (b) when it does have egress, silently reinstalls the exact dev/test tooling the build step was constructed to exclude, which is precisely the "dev dependencies leaking into the production image" risk named for this review.
  **Fix:** append `--no-dev` (and ideally `--frozen`) to all three `uv run` invocations in `docker-compose.yml:9`, e.g. `uv run --no-dev --frozen gunicorn config.wsgi ...`, or simpler: skip `uv run` at runtime entirely and invoke the venv binaries directly (`.venv/bin/python manage.py migrate &amp;&amp; ... &amp;&amp; .venv/bin/gunicorn config.wsgi ...`), which can never trigger an implicit sync.

#### Important (Should Fix)

- **`docker-compose.dev.yml:17,27` — bind mounts have no anonymous-volume guard against a pre-existing host `.venv`/`node_modules`.** `volumes: ["./backend:/app"]` and `["./frontend:/app"]` mount the host directory over the container's `/app` at runtime, which is a distinct mechanism from the build-time `.dockerignore` protection (`.dockerignore` only governs `docker build`, not bind mounts). If a developer has previously run `uv sync`/`npm install` locally outside Docker (a very plausible workflow — this repo's own top-level `backend/.venv` exists locally right now, built for Python 3.14 on macOS/arm64), that host `.venv`/`node_modules` shadows the container's own copy. The backend command re-runs `uv sync` afterward (line 16) which is likely self-healing, but the frontend command's `npm install` (line 26) is the well-known Docker footgun: `npm install` against an already-present `node_modules` for the wrong platform (e.g. macOS-only native binaries for esbuild/oxlint/rollup) does not reliably reinstall platform-correct binaries when the lockfile hasn't changed, and this exact category of corruption is the stated rationale for the `.dockerignore` files.
  **Fix:** add anonymous volumes to shield those two directories, e.g. `volumes: ["./backend:/app", "/app/.venv"]` and `["./frontend:/app", "/app/node_modules"]`.
- **`.github/workflows/ci.yml` has no migrations-drift check.** Neither job runs `manage.py makemigrations --check --dry-run`. Currently there is no drift (verified: `uv run python manage.py makemigrations --check --dry-run` → "No changes detected"), so this isn't live breakage, but it's a one-line, standard CI gate that's absent — a future model field added without its migration could pass CI if the missing column happens not to be exercised in a way that fails a test (e.g. a nullable field never asserted on). Worth adding as a `backend` job step.
- **`README.md` "Architecture in brief" feature-folder list (`README.md:128`) omits `profile`.** The line reads `features/ # auth, missions, crew, skills, assignments, matching, dashboard, settings`, but `frontend/src/features/profile/` is a real, non-trivial feature (own-skills editor, its own `api/` and `components/`, its own test file) built in commit `e9f5915`. Minor as a standalone fact, but it's exactly the kind of "README describes a different system than the one shipped" drift the task calls out — an evaluator scanning the architecture section for the my-skills page won't find it named.
- **Inconsistent secret-handling posture between `SECRET_KEY` and the database credentials in `docker-compose.yml`.** `SECRET_KEY` fails closed via `${SECRET_KEY:?...}` and `ALLOWED_HOSTS` is configurable, but the `db` service's `POSTGRES_USER`/`POSTGRES_PASSWORD` (`docker-compose.yml:4`) and the `backend`'s `DATABASE_URL` (`docker-compose.yml:11`) are hardcoded to the weak `mission`/`mission` literal with no override path at all. Low real-world exposure since the `db` service publishes no host port in the prod compose (only `docker-compose.dev.yml:8` does), but it undercuts the "this stack fails closed on secrets" claim made in the README (`README.md:179`) — that claim is true only for `SECRET_KEY`, not for the DB credential.

#### Minor (Nice to Have)

- **`README.md:107-108`** doesn't mention `.env.example` at all — the quickstart uses an inline `SECRET_KEY=$(openssl rand -hex 32) docker compose up --build` rather than pointing at the committed `.env.example`/`.env` workflow that `.env.example`'s own header comment describes. Both work, but a one-line pointer would tie the two together for a reader who goes looking for the file after reading `.env.example`.
- **`docker-compose.yml:17-20`** — the `web` (nginx) service has no `depends_on: {backend: {condition: service_healthy}}` and `backend` has no healthcheck at all, so nginx can start serving before gunicorn is ready, producing transient 502s on `/api/` right after `docker compose up`. Not fatal (retries fix it), but easy to add given `db`'s healthcheck pattern is already established in the same file.
- **`frontend/package.json`** — build output warns "Some chunks are larger than 500 kB after minification" (`index-*.js` at 742.64 kB). Not a CI failure and out of scope for a 33-task build, but worth a one-line note if this file is revisited.

### Recommendations

1. Fix the `uv run --no-dev` gap in `docker-compose.yml` before merge — it's the one finding here that can make the documented "run prod with `docker compose up`" path fail outright in a network-restricted environment, and it directly contradicts the dependency-hygiene goal the Dockerfile's `--no-dev` flag was written to satisfy.
2. Add the anonymous-volume guard to `docker-compose.dev.yml` and a `makemigrations --check` CI step — both are small, low-risk changes.
3. Add `profile` to the README's feature list and note the DB-credential/SECRET_KEY inconsistency (or explicitly scope the "fails closed on secrets" claim to `SECRET_KEY`).

### Assessment

**Ready to merge?** With fixes.
**Reasoning:** The documentation is unusually honest and accurate — all three required known limitations are present and correctly described, the demo credentials and architecture description both check out against the real code, and the claimed test/lint/build numbers all verified true when I ran them. But the confirmed, reproducible bug where the "production" compose stack downloads and installs the full dev/test dependency group from PyPI on every container start (via bare `uv run` lacking `--no-dev`) is a real, evidence-backed infra defect that undermines the multi-stage build's whole purpose and can hard-fail `docker compose up` without PyPI egress — it should be fixed before this is called done.</result>
<usage><subagent_tokens>98943</subagent_tokens><tool_uses>55</tool_uses><duration_ms>679883</duration_ms></usage>
</task-notification>

### 🤖 Assistant — 2026-08-12 09:09

All eight slices are in. **No Critical in the security core** — the tenancy invariant held across all 33 tasks. But there are two Criticals elsewhere and a substantial Important list, so I'm dispatching the fix wave in three area-scoped agents (backend, frontend, infra) run sequentially to avoid git races — rather than one agent for ~25 items across the whole stack, or one per finding.

- 🔧 **Agent** · `prompt=You are applying the **backend fixes from the final whole-branch review** of Mission Control, a completed 33-task multi-tenant Django+DRF / React SPA. All 33 tasks are implemented and individually reviewed; eight
… [14,835 more chars — see the .jsonl]`

<details><summary>⤷ Agent result</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: a9433bd04d5eaa2d1 (internal ID - do not mention to user. Use SendMessage with to: 'a9433bd04d5eaa2d1', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do
… [580 more chars — see the .jsonl]
```

</details>

### 🤖 Assistant — 2026-08-12 09:11

## Final review complete — all eight slices in

**Verdict across the board: "ready to merge with fixes."** No slice found the branch unsound; the findings are one real domain hole, one infra defect, a config fail-open, and a long tail of consistency items.

**Two Criticals:**
1. **`assignment_respond` never checks availability** — crew can accept two overlapping approved missions, the exact state the hard-block rule exists to prevent. It also wedges *both* missions out of activation. Four-line fix reusing the existing selector.
2. **The "production" compose downloads dev dependencies from PyPI on every container start** — bare `uv run` without `--no-dev` defeats the multi-stage build's whole purpose and hard-fails `docker compose up` without egress. The reviewer reproduced it against the real image.

**Plus the triage's two must-fixes:** the `DEBUG` fail-open (which it correctly identified as a *mis-classified* minor — it's the predicate that decides whether the earlier `SECRET_KEY` fix ever engages), and the raw Postgres constraint name shown to users on a normal path, which the README wrongly claims is unreachable.

What the reviewers *confirmed good* is worth stating too: the tenancy invariant holds across all nine `User.objects` sites and `objects_unscoped` never escaped into application code in 33 tasks; the availability rule genuinely exists in one place with no semantic restatement; the FSM survived four tasks touching it; migrations apply cleanly to a fresh database; and the query-count properties are pinned by tests at two data sizes rather than by comment.

The backend fix agent is running now (the Critical plus ~15 items), then frontend, then infra — sequential to avoid git races.

## 🧑 User — 2026-08-12 11:08

Can you bring up the stack please

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ docker compose -f docker-compose.dev.yml up -d 2>&1 | tail -8 ⏎ echo "=== status ===" ⏎ docker compose -f docker-compose.dev.yml ps --format '{{.Service}}\t{{.
… [33 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
Container mission-control-mutinex-frontend-1  Starting
 Container mission-control-mutinex-db-1  Starting
 Container mission-control-mutinex-frontend-1  Started
 Container mission-control-mutinex-db-1  Started
 Container mission-control-mutinex-db-1  Waiting
 Container mission-control-mutinex-db-1  Healthy
 Container mission-control-mutinex-backend-1  Starting
 Container mission-control-mutinex-backend-1  Started
=== status ===
backend	running	Up Less than a second	0.0.0.0:8000->8000/tcp, [::]:80
… [164 more chars — see the .jsonl]
```

</details>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ echo "=== waiting for vite + django ===" ⏎ for i in $(seq 1 60); do ⏎   fe=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:5173/ 2>/dev/null) ⏎   be=
… [604 more chars — see the .jsonl]`

<details><summary>⤷ Bash result ⚠️ error</summary>

```
Exit code 1
=== waiting for vite + django ===

=== login through the Vite proxy, as the browser would ===
Traceback (most recent call last):
  File "<string>", line 1, in <module>
    import sys,json;d=json.load(sys.stdin);print("access token:", "yes" if d.get("access") else "NO")
                      ~~~~~~~~~^^^^^^^^^^^
  File "/opt/homebrew/Cellar/python@3.14/3.14.6/Frameworks/Python.framework/Versions/3.14/lib/python3.14/json/__init__.py", line 298, in load
    return loads(fp.read(),
… [930 more chars — see the .jsonl]
```

</details>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ echo "=== backend log (tail) ==="; docker compose -f docker-compose.dev.yml logs backend --tail 25 2>&1 ⏎ echo; echo "=== frontend log (tail) ==="; docker comp
… [58 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
=== backend log (tail) ===
backend-1  |     self._setup(name)
backend-1  |   File "/app/.venv/lib/python3.12/site-packages/django/conf/__init__.py", line 68, in _setup
backend-1  |     self._wrapped = Settings(settings_module)
backend-1  |                     ^^^^^^^^^^^^^^^^^^^^^^^^^
backend-1  |   File "/app/.venv/lib/python3.12/site-packages/django/conf/__init__.py", line 166, in __init__
backend-1  |     mod = importlib.import_module(self.SETTINGS_MODULE)
backend-1  |           ^^^^^^^^^^^^^
… [2,107 more chars — see the .jsonl]
```

</details>

### 🤖 Assistant — 2026-08-12 11:12

The stack is up but the backend is failing — and it's failing *correctly*. The fix agent has just landed the `DEBUG` fail-open fix, so an unset `DEBUG` no longer silently defaults to `True`, which means `SECRET_KEY` is now mandatory... and `docker-compose.dev.yml` supplies neither.

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ echo "=== dev compose backend service ==="; sed -n '/^  backend:/,/^  [a-z]/p' docker-compose.dev.yml ⏎ echo "=== settings DEBUG/SECRET_KEY now ==="; sed -n '5
… [32 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
=== dev compose backend service ===
  backend:
    build: ./backend
    command: sh -c "uv sync && uv run python manage.py migrate && uv run python manage.py seed_demo && uv run python manage.py runserver 0.0.0.0:8000"
    volumes: ["./backend:/app"]
    environment:
      DATABASE_URL: postgres://mission:mission@db:5432/mission_control
    ports: ["8000:8000"]
    depends_on:
      db: {condition: service_healthy}
  frontend:
=== settings DEBUG/SECRET_KEY now ===

BASE_DIR = Path(__file__).reso
… [1,343 more chars — see the .jsonl]
```

</details>

### 🤖 Assistant — 2026-08-12 11:12

The fix itself is right and well-commented. The dev compose just needs to declare `DEBUG` — but that file is reserved for the infra agent, so I'll bring the stack up with an out-of-repo override rather than collide with it.

- 🔧 **Bash** · `command=SP=/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/scratchpad ⏎ cat > "$SP/dev-debug-override.yml" <<'EOF' ⏎ # Temporary, out-of-repo override: the DEB
… [738 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
Container mission-control-mutinex-backend-1  Recreated
 Container mission-control-mutinex-db-1  Waiting
 Container mission-control-mutinex-db-1  Healthy
 Container mission-control-mutinex-backend-1  Starting
 Container mission-control-mutinex-backend-1  Started
=== waiting for django ===
backend responding (HTTP 401) after 8x2s
```

</details>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ echo "=== services ===" ⏎ docker compose -f docker-compose.dev.yml ps --format '{{.Service}}\t{{.State}}\t{{.Ports}}' ⏎ echo; echo "=== login through the Vite
… [1,096 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
=== services ===
backend	running	0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp
db	running	0.0.0.0:5432->5432/tcp, [::]:5432->5432/tcp
frontend	running	0.0.0.0:5173->5173/tcp, [::]:5173->5173/tcp

=== login through the Vite proxy (the browser's path) ===
login OK

=== dashboard (the landing page) ===
pipeline: {'draft': 2, 'pending_approval': 2, 'approved': 1, 'rejected': 1, 'active': 1, 'completed': 1, 'cancelled': 1} | pending approvals: [{'mission_id': 19, 'name': 'Ganymede Survey', 'submitted_a
… [257 more chars — see the .jsonl]
```

</details>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ sed -n '/director@helios/,+8p' README.md | head -14`

<details><summary>⤷ Bash result</summary>

```
| Helios Aerospace | `director@helios-aerospace.test` | Director |
| Helios Aerospace | `lead@helios-aerospace.test` | Mission Lead |
| Helios Aerospace | **`crew1@helios-aerospace.test`** | Crew Member — see below |
| Helios Aerospace | `crew2`–`crew15@helios-aerospace.test` | Crew Member |
| Meridian Orbital | `director@meridian-orbital.test` | Director |
| Meridian Orbital | `lead@meridian-orbital.test` | Mission Lead |
| Meridian Orbital | `crew1`–`crew8@meridian-orbital.test` | Crew Member
… [599 more chars — see the .jsonl]
```

</details>

### 🤖 Assistant — 2026-08-12 11:13

The stack is up and serving.

**→ http://localhost:5173** (backend on :8000, Postgres on :5432)

All logins use password `orbit-demo-2026`:

| Login | Role | What to look at |
|---|---|---|
| `director@helios-aerospace.test` | Director | Dashboard, Settings, approvals |
| `lead@helios-aerospace.test` | Mission Lead | Missions, staffing panel, Auto-match |
| `crew1@helios-aerospace.test` | Crew | My Assignments — has pending, accepted *and* declined |

There's a second tenant (`…@meridian-orbital.test`) if you want to confirm isolation by logging in as each.

I verified it end to end through the Vite proxy — the dashboard returns all seven pipeline states populated, two pending approvals, 4 readiness rows with 1 at risk, 15 crew, and an `EVA Ops` skill gap. That's the seed demonstrating each feature as intended.

**One thing to know:** the backend initially refused to start, and correctly so. The fix agent had just landed the `DEBUG` fail-open fix, so an unset `DEBUG` no longer silently means `True` — which makes `SECRET_KEY` mandatory, and `docker-compose.dev.yml` declares neither. I brought it up with a temporary override held *outside* the repo (`DEBUG: "true"` for the backend service) rather than edit that file, since it's reserved for the infra fix agent that runs next. I've noted the permanent one-line fix for it.

Also worth flagging: the backend fix agent is still working, and the dev container hot-reloads on its edits — so you may hit a transient error mid-save. If something looks broken, give it a few seconds and retry before assuming it's real.

## 🧑 User — 2026-08-12 11:28

<task-notification>
<task-id>a9433bd04d5eaa2d1</task-id>
<tool-use-id>toolu_01D2fhw7UoPpDow8t423qP67</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/a9433bd04d5eaa2d1.output</output-file>
<status>completed</status>
<summary>Agent "Final fix wave: backend" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>**Status: complete — all items applied, none skipped.**

**Commits** (on `master`, from `64508d9`; `backend/` only):
- `21f6821` fix: re-check availability when a crew member accepts an assignment
- `902be3e` fix: fail-closed settings, canonical emails, and tenancy guards
- `7c38ab0` fix: give every DB constraint a human-readable violation message
- `b22a97e` fix: close the two holes in the error envelope
- `400eaca` refactor: one definition per staffing rule, business rules out of the views
- `d302f91` fix: correct skill_gaps, and read dates in the project timezone
- `f4cd30c` test: two-size query counts, a real approval race, and write RBAC
- `b4e5643` chore: seed demo dates from the project timezone

**Tests:** `437 passed in 118.07s` (was 385), `ruff check .` clean. C1, I1, I2, I3, I6 and the timezone fix were each verified RED before the fix; the T2 concurrency test fails 5/5 with the row lock neutered and passes 10/10 with it.

**Nothing skipped.** Two items were fixed differently than suggested, both deliberate and argued in the report: (1) `skill_gaps` — I *subtracted the fills* rather than renaming `open_seats`, because the frontend's zod schema requires that key; (2) `assignment_live_uniq` — `sorted(...)` does produce a spurious index-rebuild migration, so the constant is an ordered tuple with the frozenset derived from it, which removes the drift *and* keeps the migration state-only.

**Two things need you / other agents:**
1. **`docker-compose.dev.yml` needs `DEBUG: "true"`** — it sets neither DEBUG nor SECRET_KEY, so with the M1 fail-closed default its `migrate`/`seed_demo`/`runserver` now raise `ImproperlyConfigured`. One line, infra agent's file. Prod compose is already correct.
2. **Frontend follow-up for I4** — `skill_gaps` rows gained `min_proficiency` and a skill can now appear more than once, so `dashboard-page.tsx` needs a composite React key and ideally the threshold in the label. Not breaking (zod strips unknown keys) but it's a duplicate-key warning today.

Also worth knowing: `backend/.venv` was destroyed twice mid-session by a concurrent process (likely the Docker/CI agent running `uv sync`); I finished verification from an isolated scratchpad venv, so run `uv sync` before reproducing.

**Report:** `/Users/samrichards/code/mission-control-mutinex/.superpowers/sdd/00-overview/final-fix-backend.md` (that path is gitignored by `.superpowers/sdd/.gitignore`, so it is written but not committed).</result>
<usage><subagent_tokens>249746</subagent_tokens><tool_uses>131</tool_uses><duration_ms>8267896</duration_ms></usage>
</task-notification>

### 🤖 Assistant — 2026-08-12 11:29

Backend fix wave landed: **437 tests** (up from 385), ruff clean, nothing skipped — and the concurrency test I asked for was verified by neutering the row lock (fails 5/5 without it, passes 10/10 with it).

Now the frontend wave, which picks up a new follow-up the backend fix created.

- 🔧 **Agent** · `prompt=You are applying the **frontend fixes from the final whole-branch review** of Mission Control, a completed 33-task multi-tenant Django+DRF / React SPA. All tasks are implemented and individually reviewed; eight pa
… [9,291 more chars — see the .jsonl]`

<details><summary>⤷ Agent result</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: a54a2476dcae05b8a (internal ID - do not mention to user. Use SendMessage with to: 'a54a2476dcae05b8a', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do
… [580 more chars — see the .jsonl]
```

</details>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ git log --oneline 64508d9..HEAD ⏎ echo "=== stack still healthy after the backend fixes? ===" ⏎ TOK=$(curl -s -X POST http://localhost:5173/api/v1/auth/token/
… [624 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
b4e5643 chore: seed demo dates from the project timezone
f4cd30c test: two-size query counts, a real approval race, and write RBAC
d302f91 fix: correct skill_gaps, and read dates in the project timezone
400eaca refactor: one definition per staffing rule, business rules out of the views
b22a97e fix: close the two holes in the error envelope
7c38ab0 fix: give every DB constraint a human-readable violation message
902be3e fix: fail-closed settings, canonical emails, and tenancy guards
21f6821 fix:
… [320 more chars — see the .jsonl]
```

</details>

### 🤖 Assistant — 2026-08-12 11:30

Backend fixes are live on the running stack — login still works and the dashboard serves correctly. The new `skill_gaps` shape confirms the fix: 8 rows now, each carrying `min_proficiency`, because it groups by `(skill, threshold)` instead of collapsing to the lowest bar. That was the bug where five crew at proficiency 2 could hide a genuine gap at ≥9.

The eight backend commits:

```
21f6821  fix: re-check availability when a crew member accepts an assignment   ← the Critical
902be3e  fix: fail-closed settings, canonical emails, and tenancy guards
7c38ab0  fix: give every DB constraint a human-readable violation message
b22a97e  fix: close the two holes in the error envelope
400eaca  refactor: one definition per staffing rule, business rules out of the views
d302f91  fix: correct skill_gaps, and read dates in the project timezone
f4cd30c  test: two-size query counts, a real approval race, and write RBAC
b4e5643  chore: seed demo dates from the project timezone
```

One heads-up if you're clicking around right now: that `skill_gaps` change means a skill can legitimately appear twice, so the dashboard will log a React duplicate-key warning until the frontend catches up. That's in the frontend wave running now, along with the interceptor logout bug and the shared row-error helper.

## 🧑 User — 2026-08-12 11:48

<task-notification>
<task-id>a54a2476dcae05b8a</task-id>
<tool-use-id>toolu_01Jwy4p14eqBg2vujfHMsosU</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/a54a2476dcae05b8a.output</output-file>
<status>completed</status>
<summary>Agent "Final fix wave: frontend" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>Status: all done. Every item in the review (F1–F8 plus all six "also fix" items) was implemented, tested, and verified. Suite: 97/97 passing (81 baseline + 16 new), lint exit 0, build succeeds — all matching or improving on baseline.

Commits (master):
- `14a210c` fix(api-client): await the retried request so retry-still-401 forces logout (F1)
- `b945ba3` fix(auth): use the shared errorMessage() in login-form; hoist the role enum (F2)
- `ae37002` refactor(api-errors): promote rowErrorsFrom() into the shared module (F3)
- `4fa2fc7` fix(settings): surface field-level validation errors on org/skills tabs (F4)
- `c527f64` refactor(missions): one canonical TERMINAL_MISSION_STATUSES (F5)
- `a3d2f22` fix(assignments): invalidate staffing caches when an assignment is responded to (F6)
- `28eb736` fix(auth): guard RequirePermission against the loading state (F7)
- `533b89c` fix(dashboard): composite skill-gap row key and a11y cleanups (F8)
- `fec360f` fix(ui): round match-dialog swap score; alert role on mission-create fields

Test summary: 97/97 pass (16 new: interceptor retry-401/500 branches, login non-field error, shared rowErrorsFrom against both live payload shapes, profile row-error attribution, settings inline field errors, staffing-cache invalidation on respond, RequirePermission loading guard, dashboard composite skill-gap key). Each new test was verified to fail against the pre-fix code and pass after restoring the fix.

Skipped: nothing — every IMPORTANT item and every "also fix" item was applied. One correction worth noting: F3's `rowErrorsFrom` assumption in the original code was itself wrong against the live backend (it expected `extra.fields.items` to be an array; live it's an index-keyed object one level deeper for requirements, and directly on `extra.fields` for profile skills) — the new shared helper handles both real shapes.

Report: `/Users/samrichards/code/mission-control-mutinex/.superpowers/sdd/00-overview/final-fix-frontend.md` (this path is gitignored in the repo, so the file exists on disk but isn't part of the commits above).</result>
<usage><subagent_tokens>224978</subagent_tokens><tool_uses>166</tool_uses><duration_ms>1138581</duration_ms></usage>
</task-notification>

### 🤖 Assistant — 2026-08-12 11:49

Frontend wave done: **97 tests** (up from 81), nothing skipped — and it found that the row-error helper's original assumption was itself wrong against the live backend, so the shared version now handles both real shapes.

Now the last wave. It has a moving target: two fix waves just landed, so several README claims are now stale or obsolete.

- 🔧 **Agent** · `prompt=You are applying the **infrastructure, CI and documentation fixes from the final whole-branch review** of Mission Control, a completed 33-task multi-tenant Django+DRF / React SPA. This is the last of three fix wav
… [8,139 more chars — see the .jsonl]`

<details><summary>⤷ Agent result</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: ac24402a8d2b929c7 (internal ID - do not mention to user. Use SendMessage with to: 'ac24402a8d2b929c7', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do
… [580 more chars — see the .jsonl]
```

</details>

### 🤖 Assistant — 2026-08-12 11:50

Frontend wave landed clean — nine commits, **97 tests**, nothing skipped.

The final wave is running. Its most interesting task isn't the Critical (the prod stack downloading dev dependencies on every boot) but the README: two fix waves just moved the ground under it. The constraint-message limitation it documents is very likely now *fixed* rather than merely mis-described, so I've told it to verify each claim against the current code and live stack and delete what's obsolete, rather than editing the text in place. It'll also retire the temporary override I used to get the stack up, by putting `DEBUG: "true"` where it belongs.

## 🧑 User — 2026-08-12 11:59

<task-notification>
<task-id>ac24402a8d2b929c7</task-id>
<tool-use-id>toolu_0184H6VprmyCUDM9riMSser6</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/ac24402a8d2b929c7.output</output-file>
<status>completed</status>
<summary>Agent "Final fix wave: infra, CI, docs" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>Everything is clean and the dev stack is healthy and running from the repo alone. Final report follows.

Status: complete.

Commit: `17c0198` — fix(infra): stop prod stack from pulling dev deps at boot; fix dev DEBUG/mounts/CI/docs

Verification summary: Built the prod backend image and proved it now boots under `docker run --network none` (before: PyPI DNS failure trying to install pytest-django; after: `gunicorn (version 26.0.0)` with no egress), then ran the full prod stack (db+backend+web) end-to-end under a throwaway compose project confirming the healthcheck/depends_on wiring and a working `/api/v1/auth/token/` through nginx; separately brought `docker-compose.dev.yml` up from the repo alone (no override) and confirmed migrate/seed/runserver succeed with `DEBUG=true` and `curl localhost:5173/api/v1/auth/token/` returns a token, retiring your temporary override; confirmed anonymous volumes are in effect via `docker inspect`; ran `makemigrations --check --dry-run` locally (`No changes detected`); and live-tested the constraint-message fix against the running stack (duplicate skill name now returns `"A skill with this name already exists."` instead of a raw Postgres error). `pgdata` volume was never dropped — verified seeded mission count (10) survived all restarts.

Skipped: the README "stale test counts" item — checked the whole file and repo, no test counts (385/81/437/97) appear anywhere in the README, so there was nothing to update there.

Report: `/Users/samrichards/code/mission-control-mutinex/.superpowers/sdd/00-overview/final-fix-infra.md` (gitignored, same as the prior two waves' `final-fix-backend.md`/`final-fix-frontend.md`).</result>
<usage><subagent_tokens>93913</subagent_tokens><tool_uses>84</tool_uses><duration_ms>581844</duration_ms></usage>
</task-notification>

### 🤖 Assistant — 2026-08-12 11:59

All three fix waves are done. Verifying the final state before the scoped re-review.

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ git log --oneline 64508d9..HEAD | wc -l | xargs echo "fix-wave commits:" ⏎ git status --short | head ⏎ echo "=== backend ==="; cd backend && uv run pytest -q 2
… [202 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
fix-wave commits: 18
?? .agents/
?? .claude/
?? skills-lock.json
=== backend ===
........................................................................ [ 98%]
.....                                                                    [100%]
All checks passed!
=== frontend ===
 Test Files  13 passed (13)
      Tests  97 passed (97)
✓ built in 1.58s
```

</details>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex/backend && uv run pytest 2>&1 | tail -2 ⏎ echo "=== untracked dirs — mine or pre-existing? ===" ⏎ cd .. && ls -la .agents .claude 2>/dev/null | head -12; cat ski
… [35 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
.....                                                                    [100%]
437 passed in 117.30s (0:01:57)
=== untracked dirs — mine or pre-existing? ===
.agents:
total 0
drwxr-xr-x@  3 samrichards  staff   96 12 Aug 21:34 .
drwxr-xr-x@ 18 samrichards  staff  576 12 Aug 21:53 ..
drwxr-xr-x@  3 samrichards  staff   96 12 Aug 21:34 skills

.claude:
total 8
drwxr-xr-x@  4 samrichards  staff  128 12 Aug 21:34 .
drwxr-xr-x@ 18 samrichards  staff  576 12 Aug 21:53 ..
-rw-r--r--@  1 samrichards  s
… [204 more chars — see the .jsonl]
```

</details>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ D=.superpowers/sdd/00-overview ⏎ { ⏎   echo "# SCOPED RE-REVIEW OF THE FINAL FIX WAVE: 64508d9..HEAD" ⏎   echo; echo "## Commits"; git log --oneline 64508d9..H
… [319 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
243257 .superpowers/sdd/00-overview/final-fixwave.diff
```

</details>

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ D=.superpowers/sdd/00-overview ⏎ mk(){ name=$1; shift; { echo "# FIX-WAVE RE-REVIEW SLICE: $name (64508d9..HEAD)"; echo; echo "## Commits"; git log --oneline 6
… [414 more chars — see the .jsonl]`

<details><summary>⤷ Bash result</summary>

```
backend:   154141 bytes
frontend:    81875 bytes
infra:    10277 bytes
```

</details>

- 🔧 **Agent** · `prompt=You are performing the **scoped re-review of the final fix wave** on Mission Control, a completed multi-tenant Django+DRF / React SPA. A whole-branch review produced findings; three fix agents applied them. Your s
… [7,087 more chars — see the .jsonl]`

<details><summary>⤷ Agent result</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: a5f1bb646b4ea8824 (internal ID - do not mention to user. Use SendMessage with to: 'a5f1bb646b4ea8824', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do
… [580 more chars — see the .jsonl]
```

</details>

- 🔧 **Agent** · `prompt=You are performing the **scoped re-review of the final fix wave** on Mission Control, a completed multi-tenant Django+DRF / React SPA. A whole-branch review produced findings; fix agents applied them. Your slice i
… [5,380 more chars — see the .jsonl]`

<details><summary>⤷ Agent result</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: a5ff679daeb237512 (internal ID - do not mention to user. Use SendMessage with to: 'a5ff679daeb237512', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do
… [580 more chars — see the .jsonl]
```

</details>

- 🔧 **Agent** · `prompt=You are performing the **scoped re-review of the final fix wave** on Mission Control, a completed multi-tenant Django+DRF / React SPA. Your slice is the **infrastructure, CI and documentation** fixes. This is the
… [5,259 more chars — see the .jsonl]`

<details><summary>⤷ Agent result</summary>

```
Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: ace973a945dbb91d0 (internal ID - do not mention to user. Use SendMessage with to: 'ace973a945dbb91d0', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do
… [580 more chars — see the .jsonl]
```

</details>

### 🤖 Assistant — 2026-08-12 12:06

All three fix waves are in — **18 commits**, and the suites confirm the final state myself: **backend 437 passing + ruff clean, frontend 97 passing + build clean**.

The infra wave's verification is the one I most wanted: it built the production image and proved it now boots under `docker run --network none` (before, it failed on a PyPI DNS lookup trying to install pytest-django), ran the full prod stack end-to-end through nginx, and brought the dev stack up **from the repo alone** — retiring the temporary override I'd used earlier. It also live-checked the constraint fix: a duplicate skill name now returns *"A skill with this name already exists."* rather than raw Postgres text.

Scoped re-review of the fix wave is running across the same three areas. After that I'll adjudicate anything residual and hand you the branch.

## 🧑 User — 2026-08-12 13:36

<task-notification>
<task-id>a5f1bb646b4ea8824</task-id>
<tool-use-id>toolu_016etBouzhCtFas618G16iVc</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3/tasks/a5f1bb646b4ea8824.output</output-file>
<status>failed</status>
<summary>Agent "Re-review fix wave: backend" failed: Agent stalled: no progress for 600s (stream watchdog did not recover)</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>Now let me verify the claims against the actual repo state.</result>
</task-notification>

### 🤖 Assistant — 2026-08-12 18:00

The backend re-reviewer stalled. Re-dispatching it as two smaller slices to reduce the load.

- 🔧 **Bash** · `command=cd /Users/samrichards/code/mission-control-mutinex ⏎ D=.superpowers/sdd/00-overview ⏎ mk(){ name=$1; shift; { echo "# FIX-WAVE RE-REVIEW SLICE: $name (64508d9..HEAD)"; echo; echo "## Commits"; git log --oneline 6
… [321 more chars — see the .jsonl]`

<details><summary>⤷ Bash result ⚠️ error</summary>

```
claude-sonnet-5[1m] is temporarily unavailable, so auto mode cannot determine the safety of Bash right now. Wait briefly and then try this action again. If it keeps failing, continue with other tasks that don't require this action and come back to it later. Note: reading files, searching code, and other read-only operations do not require the classifier and can still be used.
```

</details>

### 🤖 Assistant — 2026-08-12 18:19

Three re-reviewers stalled simultaneously and the model backing them is reporting as temporarily unavailable — that's a platform issue, not the prompts. Bash is classifier-gated on the same model, so I'll verify the most important fix myself with read-only tools while it recovers.

- 🔧 **Read** · `file_path=/Users/samrichards/code/mission-control-mutinex/backend/mission_control/missions/services/assignments.py`

<details><summary>⤷ Read result</summary>

```
120	        # outstanding for arbitrarily long, and in the meantime a *different* mission
121	        # this crew member already accepted can be approved, hard-blocking them. The
122	        # propose-time check would then be stale, and accepting would manufacture the
123	        # one state the rest of the system assumes impossible -- two accepted
124	        # assignments on overlapping approved/active missions (spec §9's "first-approved
125	        # wins the reservation"). Same single-source
… [943 more chars — see the .jsonl]
```

</details>

### 🤖 Assistant — 2026-08-12 18:30

The Critical fix is correctly placed — scoped to the `accept` branch only, using the shared selector with `exclude_mission_id`, with a comment explaining the staleness window precisely.

- 🔧 **Bash** · `command=grep -rn "def test_.*accept" backend/tests/missions/test_assignment_apis.py | head -12`

<details><summary>⤷ Bash result</summary>

```
backend/tests/missions/test_assignment_apis.py:66:def test_crew_accepts_and_declines_own_only(auth_client_for):
backend/tests/missions/test_assignment_apis.py:448:def test_accept_is_rejected_when_a_competing_mission_was_approved_in_the_interim(
```

</details>

- 🔧 **Bash** · `command=sed -n '448,500p' backend/tests/missions/test_assignment_apis.py`

<details><summary>⤷ Bash result</summary>

```
def test_accept_is_rejected_when_a_competing_mission_was_approved_in_the_interim(
    auth_client_for,
):
    tenant, crew_c, c_client, b_id = _double_booking_setup(auth_client_for)

    # 4. C accepts on B. Before the fix this succeeded, double-booking C.
    resp = c_client.post(f"/api/v1/assignments/{b_id}/respond/", {"action": "accept"})
    assert resp.status_code == 400
    assert "overlapping" in resp.data["message"]
    assert Assignment.objects_unscoped.get(id=b_id).status == Assignment
… [1,577 more chars — see the .jsonl]
```

</details>

### 🤖 Assistant — 2026-08-12 23:05

Verified myself: the regression test walks the full four-step sequence via a shared setup helper, asserts the accept is refused and the row stays `proposed`, **and** asserts that declining still works — so the fix closes the hole without trapping the user in it. There's a companion test pinning utilization ≤ 100%, and the missing cross-tenant bulk-propose 404.

Platform looks recovered; re-dispatching the three re-reviewers.

### 🤖 Assistant — 2026-08-12 23:55

API Error: Your computer went to sleep mid-response. The response above may be incomplete.

## 🧑 User — 2026-08-14 22:40

/compact

## 🧑 User — 2026-08-14 22:42

This session is being continued from a previous conversation that ran out of context. The summary below covers the earlier portion of the conversation.

Summary:
1. **Primary Request and Intent:**

   The user's explicit request: *"Use the subagent driven superpowers skill to implement @docs/superpowers/plans/2026-08-11-mission-control/"* — a 33-task, 6-stage implementation plan for "Mission Control", a multi-tenant B2B Django+DRF / React SPA (mission planning, crew skill profiles, an auto-matching engine, an org dashboard).

   The user made four decisions during execution, all via AskUserQuestion:
   - Workspace: **"Directly on master"** (explicit consent to skip worktree/branch isolation)
   - Freeing port 5432: **"Stop the other containers"** (`mission-control-db-1`, `mission-control-web-1` from an unrelated project)
   - A series of plan-conflict rulings (see Key Technical Concepts)
   - A **STANDING RULE** granting me authority to resolve brief-vs-constraint conflicts without escalating

   Second explicit request, late in the session: *"Can you bring up the stack please"* — bring up the running dev stack.

   Operating instructions in effect from the session config: use Bash for file operations where possible; do not call the Agent tool unless requested (the user's request for subagent-driven development satisfies this); do not use workflows or deep-research.

2. **Key Technical Concepts:**
   - **superpowers:subagent-driven-development** — fresh implementer subagent per task, task review (spec + quality), fix loop capped at 5 rounds, ledger-based recovery, final whole-branch review
   - Multi-tenancy: `contextvars` + fail-closed scoped managers (`TenantModel.objects` raises `TenantContextNotSet`) + `UNIQUE(tenant_id, id)` + composite FKs
   - **`User` is the one model NOT inheriting `TenantModel`** — `User.objects` is not tenant-scoped so auth can resolve before tenant context exists; every user query must filter tenant explicitly
   - HackSoft conventions: writes in `services`, reads in `selectors`, thin `APIView`s with inline serializers
   - Seven-state mission FSM (`draft, pending_approval, approved, rejected, active, completed, cancelled`) with `MissionTransition` audit rows, atomic under `select_for_update`
   - **Availability rule (single source)**: hard-block iff *accepted* assignment on *approved/active* mission with overlapping dates (`a.start <= b.end AND b.start <= a.end`, inclusive, day granularity); everything else overlapping is a soft conflict
   - Composite tenant FKs as `DEFERRABLE INITIALLY IMMEDIATE` (not the plan's `INITIALLY DEFERRED`)
   - JWT with tenant binding from the DB row (no tenant claim), refresh rotation + blacklisting
   - Frontend: bulletproof-react feature folders, zod on every response, TanStack Query, MSW with `onUnhandledRequest: "error"`
   - Mandatory query branch order: `isLoading` → `isError` (`role="alert"`) → data

   **Human rulings recorded in `constraints.md`:**
   1. Task text governs the "one service/selector" rule (read as "no business logic in the API layer")
   2. **Every list endpoint uses `{results, count, limit, offset}`** — generalised plan-wide at Task 2.3, no exceptions
   3. INSTALLED_APPS grows as apps are created (extended by me to `AUTH_USER_MODEL` and the conftest tenant import)
   4. Error envelope governs → `extra.fields` is always a dict
   5. Prod compose fails closed on secrets
   6. zod required on the refresh response
   7. **STANDING RULE**: brief sample code that contradicts a Global Constraint loses; I apply this without escalating
   8. **Deactivated crew stop filling staffing seats**
   9. Matcher diagnosis has a **closed list of four** reasons; invariant `MAX_CREW_TOO_SMALL ⇒ open_capacity == 0` is **one-directional only**

3. **Files and Code Sections:**

   - **`.superpowers/sdd/00-overview/constraints.md`** — the authoritative contract handed to every implementer and reviewer. Contains the plan's Global Constraints verbatim plus all 9 rulings, established interface facts, the tenancy-hardening pattern, the matching-engine contract, and known limitations.

   - **`.superpowers/sdd/00-overview/progress.md`** — the SDD ledger; first line names the plan. Records every task's completion, commit range, deferred minors (~90 lines), obligations, and the five stage-gate results.

   - **`backend/mission_control/missions/services/assignments.py:120-142`** — the Critical C1 fix, which I verified personally by reading:
     ```python
             blocked = hard_blocked_user_ids(
                 start_date=assignment.mission.start_date,
                 end_date=assignment.mission.end_date,
                 exclude_mission_id=assignment.mission_id,
             )
             if actor.id in blocked:
                 raise ApplicationError("You are already committed to an overlapping mission.")
             assignment.status = AssignmentStatus.ACCEPTED
         elif action == "decline":
             assignment.status = AssignmentStatus.DECLINED
             assignment.decline_reason = reason
     ```
     Correctly scoped to the `accept` branch only, uses the shared selector, passes `exclude_mission_id`.

   - **`backend/tests/missions/test_assignment_apis.py:448-490`** — the C1 regression tests, verified by reading. `test_accept_is_rejected_when_a_competing_mission_was_approved_in_the_interim` uses a `_double_booking_setup` helper for steps 1-3, asserts step 4 returns 400 with "overlapping", the row stays `PROPOSED`, **and that declining still works** ("it is the way out of this state"). Plus `test_crew_utilization_never_exceeds_100_percent` and `test_cross_tenant_bulk_propose_404`.

   - **`backend/config/settings.py:5-30`** — the M1 fix:
     ```python
     env = environ.Env(DEBUG=(bool, False))
     # No `default=` here on purpose: django-environ consults the scheme default declared
     # above (False) only when the call passes none of its own...
     DEBUG = env("DEBUG")
     SECRET_KEY = (
         env("SECRET_KEY", default="dev-only-insecure-key-do-not-use-in-prod")
         if DEBUG else env("SECRET_KEY")
     )
     ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
     ```

   - **`backend/mission_control/missions/selectors/staffing.py`** — sole owner of the availability rule: `HARD_BLOCK_MISSION_STATUSES`, `_hard_block_qs`, `hard_blocked_user_ids`, `soft_conflicts_for_users` (omits users with no conflicts — callers must `.get(uid, [])`), `_accepted_assignments_qs` (filters `user__is_active=True`), `mission_coverage`, `staffing_validation_errors`, `mission_conflict_errors`, `committed_assignments`.

   - **`frontend/src/lib/api-errors.ts`** — shared `errorMessage`/`fieldErrorsFrom`, extended to handle both `__all__` and `non_field_errors`, and (in the fix wave) a promoted shared `rowErrorsFrom` for index-keyed list errors.

   - **`frontend/src/lib/api-client.ts`** — the axios interceptor; F1 fix awaits the retry and only logs out when the retry is itself a 401.

   - **`$SCRATCHPAD/dev-debug-override.yml`** — my temporary out-of-repo compose override adding `DEBUG: "true"`, since `docker-compose.dev.yml` was reserved for the infra agent. Since retired by commit `17c0198`.

4. **Errors and fixes:**

   - **Port 5432 occupied** by the user's other project's containers → asked the user; they chose to stop them; I did and verified the committed compose brings up a healthy Postgres.
   - **Stale dev DB schema** after `AUTH_USER_MODEL` landed → inspected `pg_stat_user_tables` to confirm all tables empty, dropped and recreated the schema, re-ran migrate.
   - **`review-package` script blocked once by the auto-mode classifier** → re-ran with an absolute path instead of a `cd &&` prefix.
   - **Wrong HEAD in a review package** (Task 4.2): I built `82fc90a..9cf39d5` but HEAD was `97b4fed` — the chore commit had landed *before* the feature commit. Checked `git log` and rebuilt the correct range.
   - **Wrong request body in my own Stage 4 gate script** — used `{"items":[{"user_id":N}]}`; the API takes `{"user_ids":[N]}`. Confirmed the brief and frontend both use `user_ids`, so no product issue; I fixed my script.
   - **745KB final-review diff** unreadable by one agent → sliced into 8 parallel area reviewers plus a triage agent.
   - **Dev stack refused to start** after the M1 fix (`ImproperlyConfigured: Set the SECRET_KEY environment variable`) — the fix working as designed, since `docker-compose.dev.yml` declared neither DEBUG nor SECRET_KEY. Resolved with an out-of-repo override rather than editing the reserved file; permanent fix delegated to the infra agent.
   - **All three fix-wave re-reviewers stalled at 600s simultaneously**, with Bash returning "claude-sonnet-5[1m] is temporarily unavailable" — a platform outage, not prompt-related. I verified the Critical fix myself with read-only tools while waiting.

   No user feedback correcting my approach was given at any point.

5. **Problem Solving:**

   Solved: 33 tasks implemented, reviewed, and fixed. Five stage gates verified live against real Postgres — these caught two defects unit tests could not (the `__all__` vs `non_field_errors` key mismatch, and raw DB constraint names reaching users). The final review found and fixed 2 Criticals, 4 must-fixes, and ~20 Important items. Test counts went 385→437 backend, 81→97 frontend.

   The single most valuable finding was C1: `assignment_respond` never re-checked availability, so crew could accept two overlapping approved missions — negating "first-approved wins the reservation", making utilization exceed 100%, and wedging **both** missions out of activation. No individual task owned that gap because each task's own guard was correct.

   The triage agent found a **mis-classification**: the `DEBUG` default was logged as a style minor at Task 1.5, but it is the predicate deciding whether that same task's Important `SECRET_KEY` fix ever engages.

   Ongoing: the scoped re-review of the fix wave has not completed.

6. **All user messages:**
   - `/model` (twice — set Opus 5 1M context, then high effort; local command output, not substantive requests)
   - *"Use the subagent driven superpowers skill to implement @docs/superpowers/plans/2026-08-11-mission-control/"*
   - AskUserQuestion answer: workspace = **"Directly on master"**
   - AskUserQuestion answers: "Task text governs (Recommended)" / "Global envelope governs (Recommended)" / "Add apps as created (Recommended)"
   - AskUserQuestion answer: port 5432 = **"Stop the other containers (Recommended)"**
   - AskUserQuestion answer: `extra.fields` = "Contract governs — coerce to dict (Recommended)"
   - AskUserQuestion answer: prod secrets = "Fail closed on missing env (Recommended)"
   - AskUserQuestion answer: list envelopes = "Global envelope, plan-wide (Recommended)"
   - AskUserQuestion answer: standing rule = "Global Constraints always govern (Recommended)"
   - AskUserQuestion answer: zod on refresh = "Global constraint governs (Recommended)"
   - AskUserQuestion answer: deactivated crew = "Deactivated crew stop filling seats (Recommended)"
   - AskUserQuestion answer: match reasons = "Add a fourth reason (Recommended)"
   - *"Can you bring up the stack please"*

7. **Pending Tasks:**
   - Complete the scoped re-review of the fix wave (3 slices: `fixwave-backend.diff` 154KB, `fixwave-frontend.diff` 82KB, `fixwave-infra.diff` 10KB — all written to `.superpowers/sdd/00-overview/`)
   - Adjudicate any residual findings (park with rulings, or stop on load-bearing ones)
   - Delete the plan workspace `.superpowers/sdd/00-overview/` once the review is clean
   - Invoke `superpowers:finishing-a-development-branch`

8. **Current Work:**

   Immediately before this summary: all three fix waves had landed (18 commits from `64508d9`), and I had personally verified the final state — **backend 437 passed + `ruff check .` clean; frontend 97 passed (13 files) + build clean**. The running dev stack was confirmed healthy, serving login and the dashboard through the Vite proxy, with the new `skill_gaps` shape (8 rows, each carrying `min_proficiency`) proving the I4 fix.

   I dispatched three scoped re-reviewers for the fix wave (backend on opus, frontend and infra on sonnet). **All three failed with "Agent stalled: no progress for 600s"**, and a Bash call returned `claude-sonnet-5[1m] is temporarily unavailable` — a platform outage.

   While waiting, I verified the Critical fix myself with read-only tools, reading `assignments.py:120-142` and the regression tests at `test_assignment_apis.py:448-490`. My final message stated: *"Platform looks recovered; re-dispatching the three re-reviewers."*

   Untracked files present and deliberately left alone (pre-existing user tooling, not part of this work): `.agents/`, `.claude/`, `skills-lock.json`.

9. **Optional Next Step:**

   Re-dispatch the three scoped fix-wave re-reviewers, whose prompts and diff slices are already prepared at `.superpowers/sdd/00-overview/fixwave-backend.diff`, `fixwave-frontend.diff`, and `fixwave-infra.diff`. This is directly continuing where I left off — my last words were *"Platform looks recovered; re-dispatching the three re-reviewers."*

   If the platform is still degraded, consider splitting the backend slice (`be-src` / `be-tests`, a split I attempted but which was interrupted by the classifier outage) to reduce stall risk.

   After the re-review returns clean, the remaining sequence is: adjudicate residuals → `rm -rf .superpowers/sdd/00-overview` → invoke `superpowers:finishing-a-development-branch`. Note the user chose to commit directly to `master`, so there is no branch to merge — the finishing skill should be told that.

If you need specific details from before compaction (like exact code snippets, error messages, or content you generated), read the full transcript at: /Users/samrichards/.claude/projects/-Users-samrichards-code-mission-control-mutinex/d074d196-5f6f-4024-805f-0640afaee2a3.jsonl
Continue the conversation from where it left off without asking the user any further questions. Resume directly — do not acknowledge the summary, do not recap what was happening, do not preface with "I'll continue" or similar. Pick up the last task as if the break never happened.

## 🧑 User — 2026-08-14 22:40

`/compact`
