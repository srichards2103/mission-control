import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { api } from "@/lib/api-client";
import { MissionStatusSchema } from "@/features/missions/api/missions";
import { PaginatedSchema } from "@/features/skills/api/skills";

export const ASSIGNMENT_STATUSES = ["proposed", "accepted", "declined", "removed"] as const;
export const AssignmentStatusSchema = z.enum(ASSIGNMENT_STATUSES);
export type AssignmentStatus = z.infer<typeof AssignmentStatusSchema>;

// --- Staffing (GET .../staffing/, and the shared response every propose/remove
// write re-serializes to, per backend/mission_control/missions/apis/assignments.py
// staffing_payload()) ---

const StaffingFilledBySchema = z.object({
  user_id: z.number(),
  name: z.string(),
  proficiency: z.number(),
});

const StaffingRequirementSchema = z.object({
  requirement_id: z.number(),
  skill_id: z.number(),
  skill_name: z.string(),
  min_proficiency: z.number(),
  required_count: z.number(),
  filled_count: z.number(),
  filled_by: z.array(StaffingFilledBySchema),
});

const SoftConflictSchema = z.object({
  mission_id: z.number(),
  mission_name: z.string(),
  mission_status: z.string(),
  assignment_status: z.string(),
});

const StaffingRosterEntrySchema = z.object({
  assignment_id: z.number(),
  user_id: z.number(),
  name: z.string(),
  status: AssignmentStatusSchema,
  // Overlapping commitments that do NOT block assigning this person — must be
  // surfaced as a warning, never treated as a reason to disable anything.
  soft_conflicts: z.array(SoftConflictSchema),
  // Held an accepted assignment on an approved/active mission with overlapping
  // dates — this is the one that actually blocks (the server already refused to
  // create a conflicting assignment; this flag describes an existing roster member
  // who has since become double-booked elsewhere).
  hard_blocked: z.boolean(),
});

export const StaffingSchema = z.object({
  requirements: z.array(StaffingRequirementSchema),
  accepted_count: z.number(),
  min_crew: z.number(),
  max_crew: z.number(),
  fully_covered: z.boolean(),
  roster: z.array(StaffingRosterEntrySchema),
});
export type Staffing = z.infer<typeof StaffingSchema>;

function staffingKey(missionId: number) {
  return ["missions", missionId, "staffing"] as const;
}

export function useStaffing(missionId: number) {
  return useQuery({
    queryKey: staffingKey(missionId),
    queryFn: async () =>
      StaffingSchema.parse((await api.get(`/missions/${missionId}/staffing/`)).data),
    enabled: Number.isFinite(missionId),
  });
}

export function invalidateStaffing(qc: ReturnType<typeof useQueryClient>, missionId: number) {
  qc.invalidateQueries({ queryKey: staffingKey(missionId) });
  qc.invalidateQueries({ queryKey: ["missions", missionId] });
}

export function useProposeAssignments(missionId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (userIds: number[]) =>
      StaffingSchema.parse(
        (await api.post(`/missions/${missionId}/assignments/`, { user_ids: userIds })).data,
      ),
    onSuccess: () => invalidateStaffing(qc, missionId),
  });
}

export function useRemoveAssignment(missionId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (assignmentId: number) =>
      StaffingSchema.parse((await api.post(`/assignments/${assignmentId}/remove/`)).data),
    onSuccess: () => invalidateStaffing(qc, missionId),
  });
}

// --- My assignments: not consumed by anything in this task (Task 4.5 only builds the
// mission-detail staffing panel), but produced here per the interface contract so
// Task 4.6's my-assignments screen can consume it without touching this file. ---

const MyAssignmentMissionSchema = z.object({
  id: z.number(),
  name: z.string(),
  status: MissionStatusSchema,
  start_date: z.string(),
  end_date: z.string(),
  description: z.string(),
});

export const MyAssignmentSchema = z.object({
  id: z.number(),
  status: AssignmentStatusSchema,
  decline_reason: z.string(),
  responded_at: z.string().nullable(),
  mission: MyAssignmentMissionSchema,
});
export type MyAssignment = z.infer<typeof MyAssignmentSchema>;

const MY_ASSIGNMENTS_KEY = ["me", "assignments"] as const;

export function useMyAssignments() {
  return useQuery({
    queryKey: MY_ASSIGNMENTS_KEY,
    queryFn: async () =>
      // Known limitation (see constraints.md): list screens fetch a hardcoded
      // limit:100 and don't paginate the UI.
      PaginatedSchema(MyAssignmentSchema).parse(
        (await api.get("/me/assignments/", { params: { limit: 100 } })).data,
      ).results,
  });
}

export function useRespondAssignment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      assignmentId,
      action,
      reason,
    }: {
      assignmentId: number;
      action: "accept" | "decline";
      reason?: string;
    }) =>
      MyAssignmentSchema.parse(
        (await api.post(`/assignments/${assignmentId}/respond/`, reason ? { action, reason } : { action }))
          .data,
      ),
    // Accepting/declining changes accepted_count, fully_covered, and the roster
    // entry's status -- exactly the staffing data propose/remove already invalidate
    // via invalidateStaffing(). Without this, a staffing panel and my-assignments
    // page co-mounted on one screen (or either query given a non-zero staleTime)
    // would show stale staffing after a respond. The response body carries the
    // mission id needed to invalidate it.
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: MY_ASSIGNMENTS_KEY });
      invalidateStaffing(qc, data.mission.id);
    },
  });
}
