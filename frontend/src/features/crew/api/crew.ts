import { useQuery } from "@tanstack/react-query";
import { z } from "zod";
import { api } from "@/lib/api-client";
import { PaginatedSchema } from "@/features/skills/api/skills";

export const CrewMemberSchema = z.object({
  id: z.number(),
  name: z.string(),
  email: z.string(),
  skills: z.array(
    z.object({
      skill_id: z.number(),
      name: z.string(),
      proficiency: z.number(),
    }),
  ),
});
export type CrewMember = z.infer<typeof CrewMemberSchema>;

export function useCrew() {
  return useQuery({
    queryKey: ["crew"],
    queryFn: async () =>
      PaginatedSchema(CrewMemberSchema).parse(
        (await api.get("/crew/", { params: { limit: 100 } })).data,
      ).results,
  });
}

export function useCrewMember(userId: number) {
  return useQuery({
    queryKey: ["crew", userId],
    queryFn: async () => CrewMemberSchema.parse((await api.get(`/crew/${userId}/`)).data),
    enabled: Number.isFinite(userId),
  });
}
