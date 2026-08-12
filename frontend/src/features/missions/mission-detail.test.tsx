import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { RouterProvider } from "react-router-dom";
import { AppProvider } from "@/app/provider";
import { createRouter } from "@/app/router";
import { Toaster } from "@/components/ui/sonner";
import { directorUser, missionFixture, server } from "@/testing/mocks";

function renderAt(path: string) {
  render(
    <AppProvider>
      <RouterProvider router={createRouter([path])} />
      <Toaster />
    </AppProvider>,
  );
}

describe("mission detail", () => {
  it("submits a draft mission", async () => {
    let posted: unknown = null;
    server.use(http.post("/api/v1/missions/10/transitions/", async ({ request }) => {
      posted = await request.json();
      return HttpResponse.json({ ...missionFixture, status: "pending_approval", history: [] });
    }));
    render(<AppProvider><RouterProvider router={createRouter(["/missions/10"])} /></AppProvider>);
    await userEvent.click(await screen.findByRole("button", { name: /submit/i }));
    expect(posted).toEqual({ action: "submit" });
  });

  it("reject requires a reason via dialog", async () => {
    server.use(http.get("/api/v1/missions/10/", () =>
      HttpResponse.json({ ...missionFixture, status: "pending_approval", created_by: { id: 99, name: "Other" } })));
    render(<AppProvider><RouterProvider router={createRouter(["/missions/10"])} /></AppProvider>);
    // default mock user is a lead without mission.review — no approve/reject rendered
    expect(await screen.findByRole("heading", { name: missionFixture.name })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /approve/i })).not.toBeInTheDocument();
  });

  it("renders the mission header: dates, crew range, and lead", async () => {
    renderAt("/missions/10");
    expect(await screen.findByRole("heading", { name: missionFixture.name })).toBeInTheDocument();
    expect(screen.getByText(/2026-09-01/)).toBeInTheDocument();
    expect(screen.getByText(/2026-09-30/)).toBeInTheDocument();
    expect(screen.getByText(/3.*6/)).toBeInTheDocument();
    expect(screen.getByText(/^Lead: Lead$/)).toBeInTheDocument();
  });

  it("shows an error state for a mission that fails to load", async () => {
    server.use(http.get("/api/v1/missions/10/", () =>
      HttpResponse.json({ message: "Server error", extra: {} }, { status: 500 })));
    renderAt("/missions/10");
    expect(await screen.findByRole("alert")).toHaveTextContent(/couldn't load this mission/i);
  });

  it("a director who is not the creator can approve, or reject with a reason", async () => {
    // Overriding GET /missions/10/ means the transitions POST handler's own
    // in-memory `missions` array (still "draft") is out of sync with what the page
    // sees ("pending_approval") — so both are overridden here, sharing one mutable
    // `missionState`, so that after a successful transition the query invalidation's
    // refetch of GET sees the update too (rather than reverting to a stale static
    // response, which is what a non-stateful override would do).
    let missionState = {
      ...missionFixture,
      status: "pending_approval",
      created_by: { id: 1, name: "Lead" },
      history: [] as { from_status: string; to_status: string; actor_name: string; reason: string; created_at: string }[],
    };
    server.use(
      http.get("/api/v1/auth/me/", () => HttpResponse.json(directorUser)),
      http.get("/api/v1/missions/10/", () => HttpResponse.json(missionState)),
      http.post("/api/v1/missions/10/transitions/", async ({ request }) => {
        const body = (await request.json()) as { action: string; reason?: string };
        missionState = {
          ...missionState,
          status: "rejected",
          history: [
            ...missionState.history,
            {
              from_status: "pending_approval",
              to_status: "rejected",
              actor_name: directorUser.name,
              reason: body.reason ?? "",
              created_at: new Date().toISOString(),
            },
          ],
        };
        return HttpResponse.json(missionState);
      }),
    );
    renderAt("/missions/10");
    expect(await screen.findByRole("button", { name: /^approve$/i })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /^reject$/i }));
    const dialog = await screen.findByRole("dialog");
    const rejectButton = within(dialog).getByRole("button", { name: /^reject$/i });
    // No reason yet: the confirm button in the dialog stays disabled.
    expect(rejectButton).toBeDisabled();

    await userEvent.type(within(dialog).getByLabelText(/reason/i), "Missing critical skills");
    expect(rejectButton).toBeEnabled();
    await userEvent.click(rejectButton);

    // Status flips and the reason shows up in history.
    expect(await screen.findByText(/^rejected$/i)).toBeInTheDocument();
    expect(await screen.findByText("Missing critical skills")).toBeInTheDocument();
  });

  it("hides approve/reject for the mission's own creator even with mission.review", async () => {
    server.use(
      http.get("/api/v1/auth/me/", () => HttpResponse.json(directorUser)),
      http.get("/api/v1/missions/10/", () =>
        HttpResponse.json({ ...missionFixture, status: "pending_approval", created_by: { id: directorUser.id, name: directorUser.name } })),
    );
    renderAt("/missions/10");
    expect(await screen.findByRole("heading", { name: missionFixture.name })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^approve$/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^reject$/i })).not.toBeInTheDocument();
  });

  it("surfaces the server's message when a transition is rejected", async () => {
    server.use(http.post("/api/v1/missions/10/transitions/", () =>
      HttpResponse.json({ message: "Needs at least one requirement.", extra: {} }, { status: 400 })));
    renderAt("/missions/10");
    await userEvent.click(await screen.findByRole("button", { name: /submit/i }));
    expect(await screen.findByText(/needs at least one requirement/i)).toBeInTheDocument();
    // Status is unchanged — still a draft, so Submit is still offered.
    expect(screen.getByRole("button", { name: /submit/i })).toBeInTheDocument();
  });

  it("shows requirements read-only once the mission has left draft/rejected", async () => {
    server.use(http.get("/api/v1/missions/10/", () =>
      HttpResponse.json({ ...missionFixture, status: "approved" })));
    renderAt("/missions/10");
    expect(await screen.findByText("Piloting")).toBeInTheDocument();
    expect(screen.getByText(/≥ 5/)).toBeInTheDocument();
    expect(screen.getByText(/× 1/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /save requirements/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /remove/i })).not.toBeInTheDocument();
  });

  it("edits requirements in draft: adds a row and saves all three fields", async () => {
    server.use(http.get("/api/v1/skills/", () =>
      HttpResponse.json({
        results: [
          { id: 1, name: "Piloting", description: "", is_archived: false },
          { id: 2, name: "Navigation", description: "", is_archived: false },
        ],
        count: 2, limit: 100, offset: 0,
      })));
    let putBody: unknown = null;
    server.use(http.put("/api/v1/missions/10/requirements/", async ({ request }) => {
      putBody = await request.json();
      return HttpResponse.json({ ...missionFixture, requirements: (putBody as { items: unknown[] }).items });
    }));
    renderAt("/missions/10");
    await screen.findByText("Piloting");

    await userEvent.click(screen.getByRole("combobox", { name: /add a skill/i }));
    await userEvent.click(await screen.findByRole("option", { name: "Navigation" }));

    await userEvent.click(screen.getByRole("button", { name: /save requirements/i }));

    expect(putBody).toEqual({
      items: [
        { skill_id: 1, min_proficiency: 5, required_count: 1 },
        { skill_id: 2, min_proficiency: 1, required_count: 1 },
      ],
    });
  });

  it("removes a requirement row", async () => {
    let putBody: unknown = null;
    server.use(http.put("/api/v1/missions/10/requirements/", async ({ request }) => {
      putBody = await request.json();
      return HttpResponse.json({ ...missionFixture, requirements: [] });
    }));
    renderAt("/missions/10");
    await screen.findByText("Piloting");
    await userEvent.click(screen.getByRole("button", { name: /remove piloting/i }));
    await userEvent.click(screen.getByRole("button", { name: /save requirements/i }));
    expect(putBody).toEqual({ items: [] });
  });

  it("shows something intelligible when the server rejects requirements with list-shaped field errors", async () => {
    server.use(http.put("/api/v1/missions/10/requirements/", () =>
      HttpResponse.json(
        {
          message: "Validation error",
          extra: { fields: { items: [{ required_count: ["Must be at least 1."] }] } },
        },
        { status: 400 },
      )));
    renderAt("/missions/10");
    await screen.findByText("Piloting");
    await userEvent.click(screen.getByRole("button", { name: /save requirements/i }));
    expect(await screen.findByText(/must be at least 1/i)).toBeInTheDocument();
  });

  it("renders history reverse-chronologically with actor, reason, and timestamp", async () => {
    server.use(http.get("/api/v1/missions/10/", () =>
      HttpResponse.json({
        ...missionFixture,
        history: [
          { from_status: "draft", to_status: "pending_approval", actor_name: "Lead", reason: "", created_at: "2026-08-01T10:00:00Z" },
          { from_status: "pending_approval", to_status: "rejected", actor_name: "Director", reason: "Needs more crew", created_at: "2026-08-02T10:00:00Z" },
        ],
      })));
    renderAt("/missions/10");
    const items = await screen.findAllByText(/moved/i);
    expect(items).toHaveLength(2);
    // Reverse-chronological: the later (rejected) entry comes first.
    expect(items[0]).toHaveTextContent(/Director moved/);
    expect(items[1]).toHaveTextContent(/Lead moved/);
    expect(screen.getByText("Needs more crew")).toBeInTheDocument();
  });
});
