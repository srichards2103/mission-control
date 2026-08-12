import { useMutation } from "@tanstack/react-query";
import { z } from "zod";
import { api } from "@/lib/api-client";

// Mirrors backend/mission_control/missions/apis/matching.py's `match_payload()`, the
// one place the wire shape of a `MatchResult` is written down server-side. Field
// names here are copied from that function and from
// backend/tests/missions/test_match_api.py's `test_response_shape_matches_dataclass_field_names`
// (which pins them by name), NOT from the task brief's shorthand
// `breakdown: {proficiency, workload, soft_conflict}` — the live contract governs
// per the plan's STANDING RULE, and the real keys are `proficiency_fit`,
// `workload_balance`, `soft_conflict_penalty`.

const SeatSchema = z.object({
  requirement_id: z.number(),
  skill_name: z.string(),
  min_proficiency: z.number(),
  proficiency: z.number(),
});

const BreakdownSchema = z.object({
  proficiency_fit: z.number(),
  workload_balance: z.number(),
  soft_conflict_penalty: z.number(),
});

// Same shape as assignments.ts's SoftConflictSchema, duplicated rather than imported:
// this feature should be able to parse the match response without depending on the
// assignments feature's internals (only its public hooks, per bulletproof-react
// cross-feature import rules).
const SoftConflictSchema = z.object({
  mission_id: z.number(),
  mission_name: z.string(),
  mission_status: z.string(),
  assignment_status: z.string(),
});

const ProposedMemberSchema = z.object({
  user_id: z.number(),
  name: z.string(),
  seats: z.array(SeatSchema),
  score: z.number(),
  breakdown: BreakdownSchema,
  workload_days: z.number(),
  soft_conflicts: z.array(SoftConflictSchema),
});
export type ProposedMember = z.infer<typeof ProposedMemberSchema>;

// The closed list of four reasons an `UnfilledSeat` can carry (matching engine
// contract, Task 5.1) — imported by name at the point of use rather than compared
// against string literals scattered through the UI.
export const NO_QUALIFIED_CREW = "no qualified crew";
export const ALL_QUALIFIED_UNAVAILABLE = "all qualified crew unavailable";
export const MAX_CREW_TOO_SMALL = "max_crew too small";
export const NOT_ENOUGH_QUALIFIED_CREW = "not enough qualified crew";

const UnfilledSeatReasonSchema = z.enum([
  NO_QUALIFIED_CREW,
  ALL_QUALIFIED_UNAVAILABLE,
  MAX_CREW_TOO_SMALL,
  NOT_ENOUGH_QUALIFIED_CREW,
]);

const UnfilledSeatSchema = z.object({
  requirement_id: z.number(),
  skill_name: z.string(),
  min_proficiency: z.number(),
  reason: UnfilledSeatReasonSchema,
});
export type UnfilledSeat = z.infer<typeof UnfilledSeatSchema>;

const AlternativeCandidateSchema = z.object({
  user_id: z.number(),
  name: z.string(),
  proficiency: z.number(),
  score: z.number(),
});
export type AlternativeCandidate = z.infer<typeof AlternativeCandidateSchema>;

const RequirementAlternativesSchema = z.object({
  requirement_id: z.number(),
  skill_name: z.string(),
  min_proficiency: z.number(),
  candidates: z.array(AlternativeCandidateSchema),
});

export const MatchResultSchema = z.object({
  team: z.array(ProposedMemberSchema),
  unfilled_seats: z.array(UnfilledSeatSchema),
  alternatives: z.array(RequirementAlternativesSchema),
  open_capacity: z.number(),
});
export type MatchResult = z.infer<typeof MatchResultSchema>;

// A mutation, not a query: running the matcher is a deliberate user action (opening
// the dialog, or hitting "Re-run"), not something to keep in sync in the background,
// and the engine is pure/read-only on the server (no assignments are made) so there
// is nothing to invalidate on success.
export function useRunMatch(missionId: number) {
  return useMutation({
    mutationFn: async () =>
      MatchResultSchema.parse((await api.post(`/missions/${missionId}/match/`)).data),
  });
}
