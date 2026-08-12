import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { api } from "@/lib/api-client";
import { PaginatedSchema } from "@/features/skills/api/skills";
import { RoleSchema } from "@/lib/roles";

export const OrgUserSchema = z.object({
  id: z.number(),
  name: z.string(),
  email: z.string(),
  role: RoleSchema,
  is_active: z.boolean(),
});
export type OrgUser = z.infer<typeof OrgUserSchema>;

export function useOrgUsers() {
  return useQuery({
    queryKey: ["settings", "users"],
    queryFn: async () =>
      PaginatedSchema(OrgUserSchema).parse(
        (await api.get("/settings/users/", { params: { limit: 100 } })).data,
      ).results,
  });
}

export function useCreateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { email: string; name: string; role: OrgUser["role"]; password: string }) =>
      OrgUserSchema.parse((await api.post("/settings/users/", input)).data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["settings", "users"] }),
  });
}

export function useUpdateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      ...patch
    }: { id: number } & Partial<Pick<OrgUser, "role" | "is_active">>) =>
      OrgUserSchema.parse((await api.patch(`/settings/users/${id}/`, patch)).data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["settings", "users"] }),
  });
}

export const OrganisationSchema = z.object({
  id: z.number(),
  name: z.string(),
  slug: z.string(),
});
export type Organisation = z.infer<typeof OrganisationSchema>;

export function useOrganisation() {
  return useQuery({
    queryKey: ["settings", "organisation"],
    queryFn: async () => OrganisationSchema.parse((await api.get("/settings/organisation/")).data),
  });
}

export function useUpdateOrganisation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { name: string }) =>
      OrganisationSchema.parse((await api.patch("/settings/organisation/", input)).data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["settings", "organisation"] }),
  });
}
