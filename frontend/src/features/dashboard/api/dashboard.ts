import { useQuery } from "@tanstack/react-query";
import { z } from "zod";
import { api } from "@/lib/api-client";
import { MissionStatusSchema } from "@/features/missions/api/missions";

// Mirrors backend/mission_control/missions/apis/dashboard.py's serializers field for
// field -- GET /api/v1/dashboard/ is a single call composing Task 6.1's four selectors
// (pipeline_summary, staffing_readiness, crew_utilization, skill_gaps) unchanged.

const StatusCountsSchema = z.object({
  draft: z.number(),
  pending_approval: z.number(),
  approved: z.number(),
  rejected: z.number(),
  active: z.number(),
  completed: z.number(),
  cancelled: z.number(),
});

const PendingApprovalSchema = z.object({
  mission_id: z.number(),
  name: z.string(),
  submitted_at: z.string(),
  age_days: z.number(),
});

const UpcomingMissionSchema = z.object({
  mission_id: z.number(),
  name: z.string(),
  start_date: z.string(),
  days_until: z.number(),
});

const PipelineSchema = z.object({
  status_counts: StatusCountsSchema,
  pending_approvals: z.array(PendingApprovalSchema),
  upcoming: z.array(UpcomingMissionSchema),
});

const ReadinessRowSchema = z.object({
  mission_id: z.number(),
  name: z.string(),
  status: MissionStatusSchema,
  start_date: z.string(),
  coverage_pct: z.number(),
  accepted_count: z.number(),
  min_crew: z.number(),
  fully_covered: z.boolean(),
  at_risk: z.boolean(),
});

const CrewUtilizationRowSchema = z.object({
  user_id: z.number(),
  name: z.string(),
  assigned_days: z.number(),
  utilization_pct: z.number(),
});

const UtilizationSchema = z.object({
  window_days: z.number(),
  org_utilization_pct: z.number(),
  crew: z.array(CrewUtilizationRowSchema),
});

const SkillGapSchema = z.object({
  skill_id: z.number(),
  skill_name: z.string(),
  open_seats: z.number(),
  qualified_crew: z.number(),
  gap: z.boolean(),
});

export const DashboardSchema = z.object({
  pipeline: PipelineSchema,
  readiness: z.array(ReadinessRowSchema),
  utilization: UtilizationSchema,
  skill_gaps: z.array(SkillGapSchema),
});
export type Dashboard = z.infer<typeof DashboardSchema>;
export type ReadinessRow = z.infer<typeof ReadinessRowSchema>;
export type CrewUtilizationRow = z.infer<typeof CrewUtilizationRowSchema>;
export type SkillGap = z.infer<typeof SkillGapSchema>;

export function useDashboard() {
  return useQuery({
    queryKey: ["dashboard"],
    queryFn: async () => DashboardSchema.parse((await api.get("/dashboard/")).data),
  });
}
