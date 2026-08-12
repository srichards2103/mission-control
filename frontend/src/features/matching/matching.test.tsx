import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { RouterProvider } from "react-router-dom";
import { AppProvider } from "@/app/provider";
import { createRouter } from "@/app/router";
import { Toaster } from "@/components/ui/sonner";
import { leadUser, missionFixture, server } from "@/testing/mocks";

function renderAt(path: string) {
  render(
    <AppProvider>
      <RouterProvider router={createRouter([path])} />
      <Toaster />
    </AppProvider>,
  );
}

async function openMatchDialog() {
  await userEvent.click(await screen.findByRole("button", { name: /auto-match/i }));
  return screen.findByRole("dialog");
}

// A two-member team, one unfilled seat, and a bench candidate for the Piloting seat --
// enough to exercise rendering, the checkbox-uncheck-then-propose flow, and the swap
// flow, per the brief's RED step plus the self-review's swap/error coverage.
const twoMemberMatch = {
  team: [
    {
      user_id: 3,
      name: "Priya Nair",
      seats: [{ requirement_id: 1, skill_name: "Piloting", min_proficiency: 7, proficiency: 9 }],
      score: 1.2,
      breakdown: { proficiency_fit: 0.9, workload_balance: 0.8, soft_conflict_penalty: 0 },
      workload_days: 5,
      soft_conflicts: [],
    },
    {
      user_id: 4,
      name: "Sam Okafor",
      seats: [{ requirement_id: 2, skill_name: "Navigation", min_proficiency: 5, proficiency: 6 }],
      score: 0.9,
      breakdown: { proficiency_fit: 0.5, workload_balance: 0.6, soft_conflict_penalty: 0 },
      workload_days: 10,
      soft_conflicts: [],
    },
  ],
  unfilled_seats: [{ requirement_id: 3, skill_name: "Engineering", min_proficiency: 9, reason: "no qualified crew" }],
  alternatives: [
    {
      requirement_id: 1,
      skill_name: "Piloting",
      min_proficiency: 7,
      candidates: [{ user_id: 5, name: "Jae Kim", proficiency: 8, score: 0.7 }],
    },
    { requirement_id: 2, skill_name: "Navigation", min_proficiency: 5, candidates: [] },
    { requirement_id: 3, skill_name: "Engineering", min_proficiency: 9, candidates: [] },
  ],
  open_capacity: 2,
};

describe("matcher dialog", () => {
  it("runs the match on open, shows the team and the unfilled seat's reason, and proposes only the checked members", async () => {
    server.use(http.post("/api/v1/missions/10/match/", () => HttpResponse.json(twoMemberMatch)));
    let posted: unknown = null;
    server.use(
      http.post("/api/v1/missions/10/assignments/", async ({ request }) => {
        posted = await request.json();
        return HttpResponse.json(
          { requirements: [], accepted_count: 0, min_crew: 3, max_crew: 6, fully_covered: false, roster: [] },
          { status: 201 },
        );
      }),
    );

    renderAt("/missions/10");
    const dialog = await openMatchDialog();

    expect(within(dialog).getByText("Priya Nair")).toBeInTheDocument();
    expect(within(dialog).getByText("Sam Okafor")).toBeInTheDocument();
    expect(within(dialog).getByText(/engineering ≥9 — no qualified crew/i)).toBeInTheDocument();

    // Both start checked (default per the brief) -- footer reflects the full team.
    expect(within(dialog).getByRole("button", { name: /propose 2 assignments/i })).toBeInTheDocument();

    await userEvent.click(within(dialog).getByRole("checkbox", { name: /sam okafor/i }));
    await userEvent.click(within(dialog).getByRole("button", { name: /propose 1 assignments/i }));

    expect(posted).toEqual({ user_ids: [3] });
  });

  it("swapping in an alternative unchecks the member it replaces and proposes the alternative instead", async () => {
    server.use(http.post("/api/v1/missions/10/match/", () => HttpResponse.json(twoMemberMatch)));
    let posted: unknown = null;
    server.use(
      http.post("/api/v1/missions/10/assignments/", async ({ request }) => {
        posted = await request.json();
        return HttpResponse.json(
          { requirements: [], accepted_count: 0, min_crew: 3, max_crew: 6, fully_covered: false, roster: [] },
          { status: 201 },
        );
      }),
    );

    renderAt("/missions/10");
    const dialog = await openMatchDialog();
    await within(dialog).findByText("Priya Nair");

    await userEvent.click(within(dialog).getByRole("combobox", { name: /swap piloting ≥7/i }));
    await userEvent.click(await screen.findByRole("option", { name: /jae kim/i }));

    // Priya (the original Piloting holder) is unchecked automatically; Jae Kim is now
    // slated in her place, and Sam is untouched -- selection is Sam + Jae, not Priya.
    expect(within(dialog).getByRole("checkbox", { name: /priya nair/i })).not.toBeChecked();
    expect(within(dialog).getByText(/swapped in: jae kim/i)).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: /propose 2 assignments/i })).toBeInTheDocument();

    await userEvent.click(within(dialog).getByRole("button", { name: /propose 2 assignments/i }));
    expect(posted).toEqual({ user_ids: [4, 5] });
  });

  it("shows the server's message when proposing the matched team is refused", async () => {
    server.use(http.post("/api/v1/missions/10/match/", () => HttpResponse.json(twoMemberMatch)));
    server.use(
      http.post("/api/v1/missions/10/assignments/", () =>
        HttpResponse.json({ message: "Unavailable for these dates: Sam Okafor.", extra: {} }, { status: 400 }),
      ),
    );

    renderAt("/missions/10");
    const dialog = await openMatchDialog();
    await within(dialog).findByText("Priya Nair");

    await userEvent.click(within(dialog).getByRole("button", { name: /propose 2 assignments/i }));

    expect(
      await within(dialog).findByText(/unavailable for these dates: sam okafor/i),
    ).toBeInTheDocument();
    // Refused, so the dialog stays open rather than closing as if it had succeeded.
    expect(dialog).toBeInTheDocument();
  });

  it("shows the server's message when the match itself is refused", async () => {
    server.use(
      http.post("/api/v1/missions/10/match/", () =>
        HttpResponse.json({ message: "Cannot match a completed or cancelled mission.", extra: {} }, { status: 400 }),
      ),
    );
    renderAt("/missions/10");
    const dialog = await openMatchDialog();
    expect(
      await within(dialog).findByText(/cannot match a completed or cancelled mission/i),
    ).toBeInTheDocument();
  });

  it("re-running the match replaces the shown team with a fresh result", async () => {
    let call = 0;
    server.use(
      http.post("/api/v1/missions/10/match/", () => {
        call += 1;
        return HttpResponse.json(
          call === 1
            ? twoMemberMatch
            : { ...twoMemberMatch, team: [twoMemberMatch.team[0]], unfilled_seats: [], alternatives: [] },
        );
      }),
    );
    renderAt("/missions/10");
    const dialog = await openMatchDialog();
    await within(dialog).findByText("Sam Okafor");

    await userEvent.click(within(dialog).getByRole("button", { name: /re-run/i }));

    await within(dialog).findByText("Priya Nair");
    expect(within(dialog).queryByText("Sam Okafor")).not.toBeInTheDocument();
  });

  it("hides the Auto-match button for a user without match.run", async () => {
    const noMatchUser = { ...leadUser, permissions: leadUser.permissions.filter((p) => p !== "match.run") };
    server.use(http.get("/api/v1/auth/me/", () => HttpResponse.json(noMatchUser)));
    renderAt("/missions/10");
    await screen.findByRole("heading", { name: missionFixture.name });
    expect(screen.queryByRole("button", { name: /auto-match/i })).not.toBeInTheDocument();
  });

  it("hides the Auto-match button once the mission is terminal", async () => {
    server.use(http.get("/api/v1/missions/10/", () => HttpResponse.json({ ...missionFixture, status: "completed" })));
    renderAt("/missions/10");
    await screen.findByRole("heading", { name: missionFixture.name });
    expect(screen.queryByRole("button", { name: /auto-match/i })).not.toBeInTheDocument();
  });
});
