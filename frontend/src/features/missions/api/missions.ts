import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { api } from "@/lib/api-client";
import { PaginatedSchema } from "@/features/skills/api/skills";

// Exact order/values per the task brief.
export const MISSION_STATUSES = [
  "draft",
  "pending_approval",
  "approved",
  "active",
  "completed",
  "rejected",
  "cancelled",
] as const;
export const MissionStatusSchema = z.enum(MISSION_STATUSES);
export type MissionStatus = z.infer<typeof MissionStatusSchema>;

const MissionCreatedBySchema = z.object({ id: z.number(), name: z.string() });

// List shape (GET /missions/, and the row shape POST /missions/ returns per-item).
export const MissionSchema = z.object({
  id: z.number(),
  name: z.string(),
  status: MissionStatusSchema,
  start_date: z.string(),
  end_date: z.string(),
  min_crew: z.number(),
  max_crew: z.number(),
  created_by: MissionCreatedBySchema,
});
export type Mission = z.infer<typeof MissionSchema>;

const MissionRequirementSchema = z.object({
  id: z.number(),
  skill_id: z.number(),
  skill_name: z.string(),
  min_proficiency: z.number(),
  required_count: z.number(),
});

const MissionTransitionSchema = z.object({
  from_status: MissionStatusSchema,
  to_status: MissionStatusSchema,
  actor_name: z.string(),
  reason: z.string(),
  created_at: z.string(),
});

// Detail shape (GET/PATCH /missions/<id>/, PUT .../requirements/, POST .../transitions/
// all re-serialize the mission this way after mutating it).
export const MissionDetailSchema = MissionSchema.extend({
  description: z.string(),
  requirements: z.array(MissionRequirementSchema),
  history: z.array(MissionTransitionSchema),
});
export type MissionDetail = z.infer<typeof MissionDetailSchema>;

export function useMissions(status?: string) {
  return useQuery({
    queryKey: ["missions", { status }],
    queryFn: async () =>
      PaginatedSchema(MissionSchema).parse(
        // Known limitation (see constraints.md): list screens fetch a hardcoded
        // limit:100 and don't paginate the UI.
        (await api.get("/missions/", { params: { limit: 100, status: status || undefined } })).data,
      ).results,
  });
}

export function useMission(id: number) {
  return useQuery({
    queryKey: ["missions", id],
    queryFn: async () => MissionDetailSchema.parse((await api.get(`/missions/${id}/`)).data),
    enabled: Number.isFinite(id),
  });
}

export type MissionCreateInput = {
  name: string;
  description?: string;
  start_date: string;
  end_date: string;
  min_crew: number;
  max_crew: number;
};

export function useCreateMission() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: MissionCreateInput) =>
      MissionDetailSchema.parse((await api.post("/missions/", input)).data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["missions"] }),
  });
}

export function useUpdateMission(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (patch: Partial<MissionCreateInput>) =>
      MissionDetailSchema.parse((await api.patch(`/missions/${id}/`, patch)).data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["missions"] }),
  });
}

export type MissionRequirementInput = {
  skill_id: number;
  min_proficiency: number;
  required_count: number;
};

export function useSetRequirements(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (items: MissionRequirementInput[]) =>
      MissionDetailSchema.parse((await api.put(`/missions/${id}/requirements/`, { items })).data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["missions"] }),
  });
}

export function useTransitionMission(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { action: string; reason?: string }) =>
      MissionDetailSchema.parse((await api.post(`/missions/${id}/transitions/`, input)).data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["missions"] }),
  });
}
