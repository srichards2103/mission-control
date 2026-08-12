import { z } from "zod";
import { api, setTokens, TokenPairSchema } from "@/lib/api-client";
import { RoleSchema } from "@/lib/roles";

export const UserSchema = z.object({
  id: z.number(),
  email: z.string(),
  name: z.string(),
  role: RoleSchema,
  tenant: z.object({ id: z.number(), name: z.string(), slug: z.string() }),
  permissions: z.array(z.string()),
});
export type User = z.infer<typeof UserSchema>;

export async function login(email: string, password: string) {
  const { data } = await api.post("/auth/token/", { email, password });
  const { access, refresh } = TokenPairSchema.parse(data);
  setTokens(access, refresh);
}

export async function fetchMe(): Promise<User> {
  const { data } = await api.get("/auth/me/");
  return UserSchema.parse(data);
}
