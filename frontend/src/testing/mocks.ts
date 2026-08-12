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

// Mutable mission list, mutated in place by the POST /api/v1/missions/ handler below
// so a created mission actually shows up on the next GET /api/v1/missions/ — the same
// "reseed in resetMockData()" reasoning as `skills`/`mySkills` above.
function initialMissions() {
  return [missionFixture];
}
let missions = initialMissions();

export function resetMockData() {
  skills = initialSkills();
  mySkills = initialMySkills();
  missions = initialMissions();
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
    let results = missions;
    if (status) results = results.filter((m) => m.status === status);
    if (search) results = results.filter((m) => m.name.toLowerCase().includes(search.toLowerCase()));
    return HttpResponse.json({ results, count: results.length, limit: 100, offset: 0 });
  }),
  http.get("/api/v1/missions/:id/", ({ params }) => {
    const mission = missions.find((m) => m.id === Number(params.id));
    if (!mission) return HttpResponse.json({ message: "Not found.", extra: {} }, { status: 404 });
    return HttpResponse.json(mission);
  }),
  http.post("/api/v1/missions/", async ({ request }) => {
    const body = (await request.json()) as {
      name: string;
      description?: string;
      start_date: string;
      end_date: string;
      min_crew: number;
      max_crew: number;
    };
    // Mirrors the two real backend CHECK constraints (mission_dates_ordered,
    // mission_crew_bounds), which full_clean() reports as extra.fields.non_field_errors
    // under the generic top-level message "Validation error" — this is the shape a real
    // 400 from this endpoint takes, and is what src/lib/api-errors.ts must unwrap.
    if (body.end_date < body.start_date) {
      return HttpResponse.json(
        {
          message: "Validation error",
          extra: { fields: { non_field_errors: ["End date must be on or after the start date."] } },
        },
        { status: 400 },
      );
    }
    if (body.max_crew < body.min_crew) {
      return HttpResponse.json(
        {
          message: "Validation error",
          extra: { fields: { non_field_errors: ["Max crew must be greater than or equal to min crew."] } },
        },
        { status: 400 },
      );
    }
    const mission = {
      id: Math.max(0, ...missions.map((m) => m.id)) + 1,
      name: body.name,
      status: "draft",
      description: body.description ?? "",
      start_date: body.start_date,
      end_date: body.end_date,
      min_crew: body.min_crew,
      max_crew: body.max_crew,
      created_by: { id: 1, name: "Lead" },
      requirements: [],
      history: [],
    };
    missions.push(mission);
    return HttpResponse.json(mission, { status: 201 });
  }),
);
