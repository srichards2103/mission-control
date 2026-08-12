import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { api } from "@/lib/api-client";

// Generic paginated-list envelope: EVERY list endpoint in this API returns
// {results, count, limit, offset} — defined once here, reused by every later feature.
export const PaginatedSchema = <T extends z.ZodTypeAny>(item: T) =>
  z.object({ results: z.array(item), count: z.number(), limit: z.number(), offset: z.number() });

export const SkillSchema = z.object({
  id: z.number(),
  name: z.string(),
  description: z.string(),
  is_archived: z.boolean(),
});
export type Skill = z.infer<typeof SkillSchema>;

export function useSkills() {
  return useQuery({
    queryKey: ["skills"],
    queryFn: async () =>
      PaginatedSchema(SkillSchema).parse((await api.get("/skills/", { params: { limit: 100 } })).data)
        .results,
  });
}

export function useCreateSkill() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { name: string; description?: string }) =>
      SkillSchema.parse((await api.post("/skills/", input)).data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["skills"] }),
  });
}

export function useUpdateSkill() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...patch }: { id: number } & Partial<Skill>) =>
      SkillSchema.parse((await api.patch(`/skills/${id}/`, patch)).data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["skills"] }),
  });
}
