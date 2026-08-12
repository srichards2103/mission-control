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

// Mutable "my skills" profile rows for the logged-in crew member, mutated in place
// by the PUT /api/v1/me/skills/ handler below (replace-the-whole-collection
// semantics — the same as the real API). Reseeded in resetMockData(), same reason
// as `skills` above.
function initialMySkills() {
  return [{ skill_id: 1, skill_name: "Piloting", proficiency: 8 }];
}
let mySkills = initialMySkills();

export const missionFixture = {
  id: 10,
  name: "Ganymede Survey",
  status: "draft",
  description: "Survey the icy moon for viable ice-mining sites.",
  start_date: "2026-09-01",
  end_date: "2026-09-30",
  min_crew: 3,
  max_crew: 6,
  created_by: { id: 1, name: "Lead" },
  requirements: [{ id: 1, skill_id: 1, skill_name: "Piloting", min_proficiency: 5, required_count: 1 }],
  history: [] as unknown[],
};

export function resetMockData() {
  skills = initialSkills();
  mySkills = initialMySkills();
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
  // NOTE: the task brief's sample shows {"items": [...]} for /api/v1/me/skills/, but
  // the real backend returns the standard paginated envelope (see
  // backend/tests/users/test_profile_api.py) per the plan-wide ruling that every list
  // endpoint uses {"results", "count", "limit", "offset"} with no exceptions. Mocked
  // here to match the live contract, not the brief's sample.
  http.get("/api/v1/me/skills/", () =>
    HttpResponse.json({ results: mySkills, count: mySkills.length, limit: 25, offset: 0 })),
  http.put("/api/v1/me/skills/", async ({ request }) => {
    const body = (await request.json()) as { items: { skill_id: number; proficiency: number }[] };
    mySkills = body.items.map((item) => ({
      skill_id: item.skill_id,
      skill_name: skills.find((s) => s.id === item.skill_id)?.name ?? `Skill ${item.skill_id}`,
      proficiency: item.proficiency,
    }));
    return HttpResponse.json({ results: mySkills, count: mySkills.length, limit: 25, offset: 0 });
  }),
  http.get("/api/v1/crew/", () =>
    HttpResponse.json({
      results: [
        {
          id: 2,
          name: "Crew Member",
          email: "crew@helios.test",
          skills: [{ skill_id: 1, name: "Piloting", proficiency: 8 }],
        },
      ],
      count: 1,
      limit: 25,
      offset: 0,
    })),
  http.get("/api/v1/crew/:id/", ({ params }) =>
    HttpResponse.json({
      id: Number(params.id),
      name: "Crew Member",
      email: "crew@helios.test",
      skills: [{ skill_id: 1, name: "Piloting", proficiency: 8 }],
    })),
  http.get("/api/v1/missions/", ({ request }) => {
    const url = new URL(request.url);
    const status = url.searchParams.get("status");
    const search = url.searchParams.get("search");
    let results = [missionFixture];
    if (status) results = results.filter((m) => m.status === status);
    if (search) results = results.filter((m) => m.name.toLowerCase().includes(search.toLowerCase()));
    return HttpResponse.json({ results, count: results.length, limit: 100, offset: 0 });
  }),
  http.get("/api/v1/missions/:id/", ({ params }) => {
    if (Number(params.id) === missionFixture.id) return HttpResponse.json(missionFixture);
    return HttpResponse.json({ message: "Not found.", extra: {} }, { status: 404 });
  }),
);
