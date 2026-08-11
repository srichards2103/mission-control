import { z } from "zod";
import { api, setTokens } from "@/lib/api-client";

export const UserSchema = z.object({
  id: z.number(),
  email: z.string(),
  name: z.string(),
  role: z.enum(["director", "mission_lead", "crew_member"]),
  tenant: z.object({ id: z.number(), name: z.string(), slug: z.string() }),
  permissions: z.array(z.string()),
});
export type User = z.infer<typeof UserSchema>;

const TokenResponseSchema = z.object({ access: z.string(), refresh: z.string() });

export async function login(email: string, password: string) {
  const { data } = await api.post("/auth/token/", { email, password });
  const { access, refresh } = TokenResponseSchema.parse(data);
  setTokens(access, refresh);
}

export async function fetchMe(): Promise<User> {
  const { data } = await api.get("/auth/me/");
  return UserSchema.parse(data);
}
