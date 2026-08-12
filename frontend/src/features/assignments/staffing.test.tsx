import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { RouterProvider } from "react-router-dom";
import { AppProvider } from "@/app/provider";
import { createRouter } from "@/app/router";
import { Toaster } from "@/components/ui/sonner";
import { leadUser, server } from "@/testing/mocks";

// A viewer with mission.view but not assignment.manage. No fixture role in mocks.ts
// combines those two (mission_lead and director both carry assignment.manage), so this
// is built inline to exercise the panel's permission gate specifically.
const viewerUser = { ...leadUser, permissions: leadUser.permissions.filter((p) => p !== "assignment.manage") };

function renderAt(path: string) {
  render(
    <AppProvider>
      <RouterProvider router={createRouter([path])} />
      <Toaster />
    </AppProvider>,
  );
}

const twoPersonRoster = {
  requirements: [
    {
      requirement_id: 1,
      skill_id: 1,
      skill_name: "Piloting",
      min_proficiency: 7,
      required_count: 2,
      filled_count: 1,
      filled_by: [{ user_id: 3, name: "Priya Nair", proficiency: 8 }],
    },
  ],
  accepted_count: 1,
  min_crew: 3,
  max_crew: 6,
  fully_covered: false,
  roster: [
    {
      assignment_id: 101,
      user_id: 3,
      name: "Priya Nair",
      status: "accepted",
      soft_conflicts: [],
      hard_blocked: false,
    },
    {
      assignment_id: 102,
      user_id: 4,
      name: "Sam Okafor",
      status: "proposed",
      soft_conflicts: [
        {
          mission_id: 20,
          mission_name: "Titan Cartography",
          mission_status: "pending_approval",
          assignment_status: "proposed",
        },
      ],
      hard_blocked: false,
    },
  ],
};

describe("staffing panel", () => {
  it("shows requirement coverage, filler names, and a conflict chip; removing a roster member posts to /remove/", async () => {
    server.use(http.get("/api/v1/missions/10/staffing/", () => HttpResponse.json(twoPersonRoster)));
    let removed: number | null = null;
    server.use(
      http.post("/api/v1/assignments/:id/remove/", ({ params }) => {
        removed = Number(params.id);
        return HttpResponse.json({ ...twoPersonRoster, roster: [] });
      }),
    );

    renderAt("/missions/10");

    // "1/2" only appears once loaded (the coverage row) -- waiting on it avoids the
    // ambiguity of "Piloting" also appearing in the (separately loaded) requirements
    // table above the staffing section.
    expect(await screen.findByText(/1\/2/)).toBeInTheDocument();
    const roster = screen.getByRole("list", { name: /roster/i });
    expect(within(roster).getByText("Priya Nair")).toBeInTheDocument();
    expect(within(roster).getByText(/conflict/i)).toBeInTheDocument();

    await userEvent.click(within(roster).getByRole("button", { name: /remove sam okafor/i }));
    expect(removed).toBe(102);
  });

  it("shows the soft conflict's mission name inside the conflict popover", async () => {
    server.use(http.get("/api/v1/missions/10/staffing/", () => HttpResponse.json(twoPersonRoster)));
    renderAt("/missions/10");
    await screen.findByText(/1\/2/);
    const roster = screen.getByRole("list", { name: /roster/i });
    await userEvent.click(within(roster).getByText(/conflict/i));
    expect(await screen.findByText(/titan cartography/i)).toBeInTheDocument();
  });

  it("shows a red unavailable chip for a hard-blocked roster member, distinct from a soft conflict", async () => {
    server.use(
      http.get("/api/v1/missions/10/staffing/", () =>
        HttpResponse.json({
          ...twoPersonRoster,
          roster: [
            {
              assignment_id: 103,
              user_id: 5,
              name: "Jae Kim",
              status: "accepted",
              soft_conflicts: [],
              hard_blocked: true,
            },
          ],
        }),
      ),
    );
    renderAt("/missions/10");
    expect(await screen.findByText(/jae kim/i)).toBeInTheDocument();
    expect(screen.getByText(/unavailable/i)).toBeInTheDocument();
    expect(screen.queryByText(/^conflict$/i)).not.toBeInTheDocument();
  });

  it("adds crew via the Add crew dialog, posting the selected user ids", async () => {
    let posted: unknown = null;
    server.use(
      http.post("/api/v1/missions/10/assignments/", async ({ request }) => {
        posted = await request.json();
        return HttpResponse.json({ ...twoPersonRoster, roster: [] }, { status: 201 });
      }),
    );
    renderAt("/missions/10");
    await userEvent.click(await screen.findByRole("button", { name: /add crew/i }));
    const dialog = await screen.findByRole("dialog");
    await userEvent.click(within(dialog).getByRole("checkbox", { name: /crew member/i }));
    await userEvent.click(within(dialog).getByRole("button", { name: /propose/i }));
    expect(posted).toEqual({ user_ids: [2] });
  });

  it("excludes a crew member already on the roster from the Add crew candidate list", async () => {
    server.use(
      http.get("/api/v1/missions/10/staffing/", () =>
        HttpResponse.json({
          ...twoPersonRoster,
          // The only crew member the base /crew/ mock returns is id 2 ("Crew Member")
          // -- putting them on the roster here should leave no candidates to propose.
          roster: [
            {
              assignment_id: 104,
              user_id: 2,
              name: "Crew Member",
              status: "proposed",
              soft_conflicts: [],
              hard_blocked: false,
            },
          ],
        }),
      ),
    );
    renderAt("/missions/10");
    await userEvent.click(await screen.findByRole("button", { name: /add crew/i }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).queryByRole("checkbox")).not.toBeInTheDocument();
    expect(await within(dialog).findByText(/no crew available to add/i)).toBeInTheDocument();
  });

  it("hides Add crew and per-row Remove for a user without assignment.manage", async () => {
    server.use(
      http.get("/api/v1/auth/me/", () => HttpResponse.json(viewerUser)),
      http.get("/api/v1/missions/10/staffing/", () => HttpResponse.json(twoPersonRoster)),
    );
    renderAt("/missions/10");
    await screen.findByText(/1\/2/);
    expect(screen.queryByRole("button", { name: /add crew/i })).not.toBeInTheDocument();
    // Scoped to the roster list: "Remove Piloting" (the unrelated requirements-editor
    // row button, gated on mission status not assignment.manage) also matches a bare
    // /remove/i, so this must not accidentally assert against that button instead.
    const roster = screen.getByRole("list", { name: /roster/i });
    expect(within(roster).queryByRole("button", { name: /^remove/i })).not.toBeInTheDocument();
  });

  it("shows both chips at once when a roster member is hard-blocked and also has a soft conflict", async () => {
    server.use(
      http.get("/api/v1/missions/10/staffing/", () =>
        HttpResponse.json({
          ...twoPersonRoster,
          roster: [
            {
              assignment_id: 105,
              user_id: 6,
              name: "Riley Chen",
              status: "accepted",
              soft_conflicts: [
                {
                  mission_id: 21,
                  mission_name: "Europa Drill",
                  mission_status: "draft",
                  assignment_status: "proposed",
                },
              ],
              hard_blocked: true,
            },
          ],
        }),
      ),
    );
    renderAt("/missions/10");
    expect(await screen.findByText(/riley chen/i)).toBeInTheDocument();
    // The two conditionals are independent, not mutually exclusive -- both chips
    // render for the same roster row.
    expect(screen.getByText(/unavailable/i)).toBeInTheDocument();
    expect(screen.getByText(/^conflict$/i)).toBeInTheDocument();
  });

  it("shows the server's message inline in the Add crew dialog when propose is refused (e.g. a hard-blocked candidate)", async () => {
    server.use(
      http.post("/api/v1/missions/10/assignments/", () =>
        HttpResponse.json(
          { message: "Unavailable for these dates: Crew Member.", extra: {} },
          { status: 400 },
        ),
      ),
    );
    renderAt("/missions/10");
    await userEvent.click(await screen.findByRole("button", { name: /add crew/i }));
    const dialog = await screen.findByRole("dialog");
    await userEvent.click(within(dialog).getByRole("checkbox", { name: /crew member/i }));
    await userEvent.click(within(dialog).getByRole("button", { name: /propose/i }));
    // Inline, scoped to the still-open dialog -- not just a toast the user might miss.
    expect(await within(dialog).findByText(/unavailable for these dates: crew member/i)).toBeInTheDocument();
    expect(dialog).toBeInTheDocument();
  });

  it("shows the server's message via toast when removing a roster member is refused", async () => {
    server.use(http.get("/api/v1/missions/10/staffing/", () => HttpResponse.json(twoPersonRoster)));
    server.use(
      http.post("/api/v1/assignments/:id/remove/", () =>
        HttpResponse.json(
          { message: "Only proposed or accepted assignments can be removed.", extra: {} },
          { status: 400 },
        ),
      ),
    );
    renderAt("/missions/10");
    await screen.findByText(/1\/2/);
    const roster = screen.getByRole("list", { name: /roster/i });
    await userEvent.click(within(roster).getByRole("button", { name: /remove sam okafor/i }));
    // Remove has no form to attach an inline error to (single click per row, no
    // surrounding form state) -- the toast is the only surface, per the existing
    // transition-buttons.tsx pattern for bare actions.
    expect(
      await screen.findByText(/only proposed or accepted assignments can be removed/i),
    ).toBeInTheDocument();
  });

  it("only disables the row being removed while its removal is in flight, not every row", async () => {
    server.use(http.get("/api/v1/missions/10/staffing/", () => HttpResponse.json(twoPersonRoster)));
    // A mutable holder object rather than a bare `let` -- a bare `let resolve: T | null`
    // reassigned only inside this nested closure trips a TS control-flow-narrowing
    // quirk that types the later `resolveRemove?.()` call as `never`.
    const deferred: { resolve: (() => void) | null } = { resolve: null };
    server.use(
      http.post("/api/v1/assignments/:id/remove/", async () => {
        await new Promise<void>((resolve) => {
          deferred.resolve = resolve;
        });
        return HttpResponse.json(twoPersonRoster);
      }),
    );
    renderAt("/missions/10");
    await screen.findByText(/1\/2/);
    const roster = screen.getByRole("list", { name: /roster/i });
    const removeSam = within(roster).getByRole("button", { name: /remove sam okafor/i });
    const removePriya = within(roster).getByRole("button", { name: /remove priya nair/i });

    await userEvent.click(removeSam);
    expect(removeSam).toBeDisabled();
    expect(removePriya).toBeEnabled();

    deferred.resolve?.();
    await waitFor(() => expect(removeSam).toBeEnabled());
  });

  it("shows an error state when staffing fails to load", async () => {
    server.use(
      http.get("/api/v1/missions/10/staffing/", () =>
        HttpResponse.json({ message: "Server error", extra: {} }, { status: 500 })),
    );
    renderAt("/missions/10");
    expect(await screen.findByRole("alert")).toHaveTextContent(/couldn't load staffing/i);
  });
});
