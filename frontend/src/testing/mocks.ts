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

// Static dashboard fixture (GET /api/v1/dashboard/) -- nothing in this feature writes
// to it, so unlike skills/missions/staffing/myAssignments above it needs no mutable
// backing store or resetMockData() entry.
export const dashboardFixture = {
  pipeline: {
    status_counts: {
      draft: 1,
      pending_approval: 1,
      approved: 1,
      rejected: 0,
      active: 1,
      completed: 0,
      cancelled: 0,
    },
    pending_approvals: [
      { mission_id: 20, name: "Titan Cartography", submitted_at: "2026-08-10T12:00:00Z", age_days: 2 },
    ],
    upcoming: [{ mission_id: 21, name: "Europa Drill", start_date: "2026-08-20", days_until: 8 }],
  },
  readiness: [
    {
      mission_id: 22,
      name: "Ganymede Survey",
      status: "approved",
      start_date: "2026-09-01",
      coverage_pct: 33,
      accepted_count: 1,
      min_crew: 3,
      fully_covered: false,
      at_risk: true,
    },
    {
      mission_id: 23,
      name: "Callisto Relay",
      status: "active",
      start_date: "2026-08-15",
      coverage_pct: 100,
      accepted_count: 4,
      min_crew: 4,
      fully_covered: true,
      at_risk: false,
    },
  ],
  utilization: {
    window_days: 90,
    org_utilization_pct: 42,
    crew: [
      { user_id: 2, name: "Priya Nair", assigned_days: 60, utilization_pct: 67 },
      { user_id: 3, name: "Sam Okafor", assigned_days: 10, utilization_pct: 11 },
    ],
  },
  skill_gaps: [
    { skill_id: 1, skill_name: "Piloting", open_seats: 3, qualified_crew: 1, gap: true },
    { skill_id: 2, skill_name: "Navigation", open_seats: 1, qualified_crew: 4, gap: false },
  ],
};

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

// Mutable staffing state, keyed by mission id. Mutated in place by the bulk-propose and
// remove handlers below so the staffing panel's mutations (which invalidate and refetch
// GET .../staffing/) actually see the effect of a prior POST — same "reseed in
// resetMockData()" reasoning as `skills`/`mySkills`/`missions` above. Default entry
// mirrors `missionFixture`'s single Piloting requirement so every existing
// mission-detail test (which now also renders the staffing panel) gets a schema-valid
// response even though it never asserts on it.
type StaffingFilledBy = { user_id: number; name: string; proficiency: number };
type StaffingRequirement = {
  requirement_id: number;
  skill_id: number;
  skill_name: string;
  min_proficiency: number;
  required_count: number;
  filled_count: number;
  filled_by: StaffingFilledBy[];
};
type SoftConflict = {
  mission_id: number;
  mission_name: string;
  mission_status: string;
  assignment_status: string;
};
type RosterEntry = {
  assignment_id: number;
  user_id: number;
  name: string;
  status: "proposed" | "accepted" | "declined" | "removed";
  soft_conflicts: SoftConflict[];
  hard_blocked: boolean;
};
type Staffing = {
  requirements: StaffingRequirement[];
  accepted_count: number;
  min_crew: number;
  max_crew: number;
  fully_covered: boolean;
  roster: RosterEntry[];
};

// Mutable "my assignments" rows for the logged-in crew member, mutated in place by the
// POST /api/v1/assignments/:id/respond/ handler below — same "reseed in
// resetMockData()" reasoning as `skills`/`mySkills`/`missions`/`staffing` above.
type MyAssignment = {
  id: number;
  status: "proposed" | "accepted" | "declined" | "removed";
  decline_reason: string;
  responded_at: string | null;
  mission: {
    id: number;
    name: string;
    status: string;
    start_date: string;
    end_date: string;
    description: string;
  };
};

function initialMyAssignments(): MyAssignment[] {
  return [
    {
      id: 1,
      status: "proposed",
      decline_reason: "",
      responded_at: null,
      mission: {
        id: 10,
        name: "Ganymede Survey",
        status: "draft",
        start_date: "2026-09-01",
        end_date: "2026-09-30",
        description: "Survey the icy moon for viable ice-mining sites.",
      },
    },
    {
      id: 2,
      status: "accepted",
      decline_reason: "",
      responded_at: "2026-08-01T12:00:00Z",
      mission: {
        id: 11,
        name: "Titan Cartography",
        status: "approved",
        start_date: "2026-10-01",
        end_date: "2026-10-15",
        description: "Map Titan's methane lakes.",
      },
    },
  ];
}
let myAssignments = initialMyAssignments();

function initialStaffing(): Record<number, Staffing> {
  return {
    10: {
      requirements: [
        {
          requirement_id: 1,
          skill_id: 1,
          skill_name: "Piloting",
          min_proficiency: 5,
          required_count: 1,
          filled_count: 0,
          filled_by: [],
        },
      ],
      accepted_count: 0,
      min_crew: 3,
      max_crew: 6,
      fully_covered: false,
      roster: [],
    },
  };
}
let staffing = initialStaffing();

export function resetMockData() {
  skills = initialSkills();
  mySkills = initialMySkills();
  missions = initialMissions();
  staffing = initialStaffing();
  myAssignments = initialMyAssignments();
}

export const server = setupServer(
  http.post("/api/v1/auth/token/", () => HttpResponse.json({ access: "a", refresh: "r" })),
  http.get("/api/v1/auth/me/", () => HttpResponse.json(leadUser)),
  http.get("/api/v1/dashboard/", () => HttpResponse.json(dashboardFixture)),
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
  http.put("/api/v1/missions/:id/requirements/", async ({ params, request }) => {
    const index = missions.findIndex((m) => m.id === Number(params.id));
    if (index === -1) return HttpResponse.json({ message: "Not found.", extra: {} }, { status: 404 });
    const body = (await request.json()) as {
      items: { skill_id: number; min_proficiency: number; required_count: number }[];
    };
    // Replace the array slot with a new object rather than mutating the found
    // mission in place — the found object may be `missionFixture` itself
    // (shared by reference through initialMissions()), and mutating it directly
    // would leak across tests despite resetMockData() reseeding `missions`.
    const updated = {
      ...missions[index],
      requirements: body.items.map((item, i) => ({
        id: i + 1,
        skill_id: item.skill_id,
        skill_name: skills.find((s) => s.id === item.skill_id)?.name ?? `Skill ${item.skill_id}`,
        min_proficiency: item.min_proficiency,
        required_count: item.required_count,
      })),
    };
    missions[index] = updated;
    return HttpResponse.json(updated);
  }),
  http.post("/api/v1/missions/:id/transitions/", async ({ params, request }) => {
    const index = missions.findIndex((m) => m.id === Number(params.id));
    if (index === -1) return HttpResponse.json({ message: "Not found.", extra: {} }, { status: 404 });
    const mission = missions[index];
    const body = (await request.json()) as { action: string; reason?: string };
    // A light stand-in for the real seven-state FSM (see backend + constraints.md) —
    // just enough for these components to exercise a real request/response round
    // trip. The actual guards (permissions, dates, ≥1 requirement, no self-approval)
    // are backend-tested elsewhere; this mock only needs valid-from-state + reason
    // presence so tests can assert the UI surfaces a 400's message correctly.
    const TRANSITIONS: Record<string, { from: string[]; to: string }> = {
      submit: { from: ["draft"], to: "pending_approval" },
      approve: { from: ["pending_approval"], to: "approved" },
      reject: { from: ["pending_approval"], to: "rejected" },
      revise: { from: ["rejected"], to: "draft" },
      activate: { from: ["approved"], to: "active" },
      complete: { from: ["active"], to: "completed" },
      cancel: { from: ["draft", "pending_approval", "approved", "active"], to: "cancelled" },
    };
    const def = TRANSITIONS[body.action];
    if (!def || !def.from.includes(mission.status)) {
      return HttpResponse.json(
        { message: "That transition isn't allowed right now.", extra: {} },
        { status: 400 },
      );
    }
    if ((body.action === "reject" || body.action === "cancel") && !body.reason) {
      return HttpResponse.json({ message: "A reason is required.", extra: {} }, { status: 400 });
    }
    const updated = {
      ...mission,
      status: def.to,
      history: [
        ...mission.history,
        {
          from_status: mission.status,
          to_status: def.to,
          actor_name: "Lead",
          reason: body.reason ?? "",
          created_at: new Date().toISOString(),
        },
      ],
    };
    missions[index] = updated;
    return HttpResponse.json(updated);
  }),
  http.get("/api/v1/missions/:id/staffing/", ({ params }) => {
    const found = staffing[Number(params.id)];
    if (!found) return HttpResponse.json({ message: "Not found.", extra: {} }, { status: 404 });
    return HttpResponse.json(found);
  }),
  // Default match response: an empty proposal with no unfilled seats and full
  // remaining capacity. Individual matcher tests override this via server.use() to
  // exercise a real team/unfilled-seats/alternatives payload -- this base handler only
  // exists so `onUnhandledRequest: "error"` doesn't fail every *other* test that now
  // renders the (permission-gated) Auto-match button but never clicks it.
  http.post("/api/v1/missions/:id/match/", ({ params }) => {
    const mission = missions.find((m) => m.id === Number(params.id));
    if (!mission) return HttpResponse.json({ message: "Not found.", extra: {} }, { status: 404 });
    if (mission.status === "completed" || mission.status === "cancelled") {
      return HttpResponse.json(
        { message: "Cannot match a completed or cancelled mission.", extra: {} },
        { status: 400 },
      );
    }
    return HttpResponse.json({ team: [], unfilled_seats: [], alternatives: [], open_capacity: mission.max_crew });
  }),
  http.post("/api/v1/missions/:id/assignments/", async ({ params, request }) => {
    const missionId = Number(params.id);
    const found = staffing[missionId];
    if (!found) return HttpResponse.json({ message: "Not found.", extra: {} }, { status: 404 });
    const body = (await request.json()) as { user_ids: number[] };
    let nextAssignmentId = Math.max(0, ...found.roster.map((r) => r.assignment_id)) + 1;
    const added: RosterEntry[] = body.user_ids.map((userId) => ({
      assignment_id: nextAssignmentId++,
      user_id: userId,
      name: `Crew ${userId}`,
      status: "proposed",
      soft_conflicts: [],
      hard_blocked: false,
    }));
    const updated = { ...found, roster: [...found.roster, ...added] };
    staffing[missionId] = updated;
    return HttpResponse.json(updated, { status: 201 });
  }),
  http.post("/api/v1/assignments/:id/remove/", ({ params }) => {
    const assignmentId = Number(params.id);
    const missionId = Object.keys(staffing)
      .map(Number)
      .find((id) => staffing[id].roster.some((r) => r.assignment_id === assignmentId));
    if (missionId === undefined) {
      return HttpResponse.json({ message: "Not found.", extra: {} }, { status: 404 });
    }
    const found = staffing[missionId];
    const updated = { ...found, roster: found.roster.filter((r) => r.assignment_id !== assignmentId) };
    staffing[missionId] = updated;
    return HttpResponse.json(updated);
  }),
  http.get("/api/v1/me/assignments/", () =>
    HttpResponse.json({ results: myAssignments, count: myAssignments.length, limit: 100, offset: 0 })),
  http.post("/api/v1/assignments/:id/respond/", async ({ params, request }) => {
    const assignmentId = Number(params.id);
    const index = myAssignments.findIndex((a) => a.id === assignmentId);
    if (index === -1) return HttpResponse.json({ message: "Not found.", extra: {} }, { status: 404 });
    const current = myAssignments[index];
    // Mirrors the real backend rule: only a `proposed` assignment can be responded to.
    if (current.status !== "proposed") {
      return HttpResponse.json(
        { message: "This assignment can no longer be responded to.", extra: {} },
        { status: 400 },
      );
    }
    const body = (await request.json()) as { action: "accept" | "decline"; reason?: string };
    const updated: MyAssignment = {
      ...current,
      status: body.action === "accept" ? "accepted" : "declined",
      decline_reason: body.action === "decline" ? (body.reason ?? "") : "",
      responded_at: new Date().toISOString(),
    };
    myAssignments[index] = updated;
    return HttpResponse.json(updated);
  }),
);
