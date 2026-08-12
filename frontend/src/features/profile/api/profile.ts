import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { api } from "@/lib/api-client";
import { PaginatedSchema } from "@/features/skills/api/skills";

// NOTE: the task brief's sample code has GET/PUT /api/v1/me/skills/ returning
// {"items": [...]}. The backend actually returns the standard paginated envelope
// (confirmed in backend/tests/users/test_profile_api.py), per the plan-wide ruling
// that every list endpoint uses {"results", "count", "limit", "offset"} with no
// exceptions (constraints.md, "Ruling 2, generalised plan-wide"). We follow the
// live backend/global constraint here, not the brief's sample shape.
export const MySkillSchema = z.object({
  skill_id: z.number(),
  skill_name: z.string(),
  proficiency: z.number(),
});
export type MySkill = z.infer<typeof MySkillSchema>;

export function useMySkills() {
  return useQuery({
    queryKey: ["me", "skills"],
    queryFn: async () =>
      PaginatedSchema(MySkillSchema).parse(
        (await api.get("/me/skills/", { params: { limit: 100 } })).data,
      ).results,
  });
}

export function useSetMySkills() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (items: { skill_id: number; proficiency: number }[]) =>
      PaginatedSchema(MySkillSchema).parse((await api.put("/me/skills/", { items })).data).results,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["me", "skills"] }),
  });
}
