import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";

export const leadUser = {
  id: 1, email: "lead@helios.test", name: "Lead", role: "mission_lead",
  tenant: { id: 1, name: "Helios", slug: "helios" },
  permissions: ["mission.view", "mission.create", "mission.edit", "mission.progress",
    "assignment.manage", "match.run", "crew.view", "skill.view", "dashboard.view"],
};
export const crewUser = {
  ...leadUser, id: 2, email: "crew@helios.test", role: "crew_member",
  permissions: ["skill.view", "own_skills.edit", "assignment.respond"],
};
export const directorUser = {
  ...leadUser, id: 3, email: "director@helios.test", name: "Director", role: "director",
  is_active: true,
  permissions: [
    "mission.view", "mission.create", "mission.edit", "mission.progress", "mission.review",
    "assignment.manage", "match.run", "crew.view", "user.manage", "skill.view", "skill.manage",
    "settings.view", "settings.manage", "dashboard.view",
  ],
};

// Mutable mock data for handlers below (e.g. the skills POST handler appends to this
// array). server.resetHandlers() only resets handler *overrides* added via server.use(),
// not data mutated by a still-registered base handler — so this must be reseeded
// explicitly between tests. See resetMockData(), wired into afterEach in setup.ts.
function initialSkills() {
  return [{ id: 1, name: "Piloting", description: "", is_archived: false }];
}
let skills = initialSkills();

export function resetMockData() {
  skills = initialSkills();
}

export const server = setupServer(
  http.post("/api/v1/auth/token/", () => HttpResponse.json({ access: "a", refresh: "r" })),
  http.get("/api/v1/auth/me/", () => HttpResponse.json(leadUser)),
  http.get("/api/v1/skills/", () =>
    HttpResponse.json({ results: skills, count: skills.length, limit: 25, offset: 0 })),
  http.post("/api/v1/skills/", async ({ request }) => {
    const body = (await request.json()) as { name: string };
    const skill = { id: skills.length + 1, name: body.name, description: "", is_archived: false };
    skills.push(skill);
    return HttpResponse.json(skill, { status: 201 });
  }),
  http.get("/api/v1/settings/users/", () =>
    HttpResponse.json({ results: [directorUser], count: 1, limit: 25, offset: 0 })),
  http.get("/api/v1/settings/organisation/", () =>
    HttpResponse.json({ id: 1, name: "Helios", slug: "helios" })),
);
