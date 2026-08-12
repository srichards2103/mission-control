import { z } from "zod";

// The three-role enum and their display labels, previously duplicated in
// features/auth/api/auth.ts, features/settings/api/settings.ts, and (with labels)
// features/settings/components/users-tab.tsx. Hoisted here so the three copies can't
// drift out of sync.
export const ROLES = ["director", "mission_lead", "crew_member"] as const;
export const RoleSchema = z.enum(ROLES);
export type Role = z.infer<typeof RoleSchema>;

export const ROLE_LABELS: Record<Role, string> = {
  director: "Director",
  mission_lead: "Mission Lead",
  crew_member: "Crew Member",
};

export const ROLE_OPTIONS: { value: Role; label: string }[] = ROLES.map((value) => ({
  value,
  label: ROLE_LABELS[value],
}));

export function roleLabel(role: string): string {
  return ROLE_LABELS[role as Role] ?? role;
}
