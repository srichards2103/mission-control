import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { RouterProvider } from "react-router-dom";
import { AppProvider } from "@/app/provider";
import { createRouter } from "@/app/router";
import { Toaster } from "@/components/ui/sonner";
import { crewUser, server } from "@/testing/mocks";

function renderAt(path: string) {
  render(
    <AppProvider>
      <RouterProvider router={createRouter([path])} />
      <Toaster />
    </AppProvider>,
  );
}

const proposedFixture = {
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
};

const acceptedFixture = {
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
};

function mockAssignments(items: unknown[]) {
  server.use(
    http.get("/api/v1/me/assignments/", () =>
      HttpResponse.json({ results: items, count: items.length, limit: 100, offset: 0 })),
  );
}

describe("my assignments", () => {
  it("accepts a pending proposal, posting {action: accept} and moving the card into Upcoming", async () => {
    server.use(http.get("/api/v1/auth/me/", () => HttpResponse.json(crewUser)));
    mockAssignments([proposedFixture, acceptedFixture]);
    let posted: unknown = null;
    server.use(
      http.post("/api/v1/assignments/1/respond/", async ({ request }) => {
        posted = await request.json();
        mockAssignments([{ ...proposedFixture, status: "accepted", responded_at: "2026-08-11T00:00:00Z" }, acceptedFixture]);
        return HttpResponse.json({ ...proposedFixture, status: "accepted", responded_at: "2026-08-11T00:00:00Z" });
      }),
    );

    renderAt("/my-assignments");

    const pendingSection = (await screen.findByRole("heading", { name: /pending proposals/i })).closest(
      "section",
    ) as HTMLElement;
    expect(within(pendingSection).getByText("Ganymede Survey")).toBeInTheDocument();

    await userEvent.click(within(pendingSection).getByRole("button", { name: /^accept$/i }));

    expect(posted).toEqual({ action: "accept" });
    expect(await screen.findByText(/no pending proposals/i)).toBeInTheDocument();

    const upcomingSection = screen.getByRole("heading", { name: /^upcoming$/i }).closest(
      "section",
    ) as HTMLElement;
    expect(within(upcomingSection).getAllByText("Ganymede Survey").length).toBeGreaterThan(0);
  });

  it("declines a proposal with a reason via the decline dialog", async () => {
    server.use(http.get("/api/v1/auth/me/", () => HttpResponse.json(crewUser)));
    mockAssignments([proposedFixture]);
    let posted: unknown = null;
    server.use(
      http.post("/api/v1/assignments/1/respond/", async ({ request }) => {
        posted = await request.json();
        const updated = {
          ...proposedFixture,
          status: "declined",
          decline_reason: "Double-booked",
          responded_at: "2026-08-11T00:00:00Z",
        };
        mockAssignments([updated]);
        return HttpResponse.json(updated);
      }),
    );

    renderAt("/my-assignments");

    await userEvent.click(await screen.findByRole("button", { name: /^decline$/i }));
    const dialog = await screen.findByRole("dialog");
    await userEvent.type(within(dialog).getByLabelText(/reason/i), "Double-booked");
    await userEvent.click(within(dialog).getByRole("button", { name: /^decline$/i }));

    expect(posted).toEqual({ action: "decline", reason: "Double-booked" });
    expect(await screen.findByText(/no pending proposals/i)).toBeInTheDocument();
  });

  it("declines a proposal with no reason, omitting reason from the request body", async () => {
    server.use(http.get("/api/v1/auth/me/", () => HttpResponse.json(crewUser)));
    mockAssignments([proposedFixture]);
    let posted: unknown = null;
    server.use(
      http.post("/api/v1/assignments/1/respond/", async ({ request }) => {
        posted = await request.json();
        return HttpResponse.json({ ...proposedFixture, status: "declined", responded_at: "2026-08-11T00:00:00Z" });
      }),
    );

    renderAt("/my-assignments");

    await userEvent.click(await screen.findByRole("button", { name: /^decline$/i }));
    const dialog = await screen.findByRole("dialog");
    await userEvent.click(within(dialog).getByRole("button", { name: /^decline$/i }));

    expect(posted).toEqual({ action: "decline" });
  });

  it("shows the server's message when responding is refused (e.g. a 400 on an already-handled assignment)", async () => {
    server.use(http.get("/api/v1/auth/me/", () => HttpResponse.json(crewUser)));
    mockAssignments([proposedFixture]);
    server.use(
      http.post("/api/v1/assignments/1/respond/", () =>
        HttpResponse.json(
          { message: "This assignment can no longer be responded to.", extra: {} },
          { status: 400 },
        ),
      ),
    );

    renderAt("/my-assignments");

    await userEvent.click(await screen.findByRole("button", { name: /^accept$/i }));

    expect(
      await screen.findByText(/this assignment can no longer be responded to/i),
    ).toBeInTheDocument();
    // Still pending -- the failed response must not have removed the card.
    expect(screen.getByText("Ganymede Survey")).toBeInTheDocument();
  });

  it("shows Upcoming and History groups with empty states, and mutes history entries", async () => {
    server.use(http.get("/api/v1/auth/me/", () => HttpResponse.json(crewUser)));
    mockAssignments([
      acceptedFixture,
      {
        id: 3,
        status: "declined",
        decline_reason: "Not available",
        responded_at: "2026-07-01T00:00:00Z",
        mission: {
          id: 12,
          name: "Europa Drill",
          status: "draft",
          start_date: "2026-06-01",
          end_date: "2026-06-10",
          description: "",
        },
      },
      {
        id: 4,
        status: "accepted",
        decline_reason: "",
        responded_at: "2026-05-01T00:00:00Z",
        mission: {
          id: 13,
          name: "Callisto Survey",
          status: "completed",
          start_date: "2026-01-01",
          end_date: "2026-01-10",
          description: "",
        },
      },
    ]);

    renderAt("/my-assignments");

    expect(await screen.findByText(/no pending proposals/i)).toBeInTheDocument();
    const upcomingSection = screen.getByRole("heading", { name: /^upcoming$/i }).closest(
      "section",
    ) as HTMLElement;
    expect(within(upcomingSection).getByText("Titan Cartography")).toBeInTheDocument();

    const historySection = screen.getByRole("heading", { name: /^history$/i }).closest(
      "section",
    ) as HTMLElement;
    expect(within(historySection).getByText("Europa Drill")).toBeInTheDocument();
    expect(within(historySection).getByText(/not available/i)).toBeInTheDocument();
    // A completed mission's accepted assignment belongs in History, not Upcoming.
    expect(within(historySection).getByText("Callisto Survey")).toBeInTheDocument();
    expect(within(upcomingSection).queryByText("Callisto Survey")).not.toBeInTheDocument();
  });

  it("shows an error state when assignments fail to load", async () => {
    server.use(http.get("/api/v1/auth/me/", () => HttpResponse.json(crewUser)));
    server.use(
      http.get("/api/v1/me/assignments/", () =>
        HttpResponse.json({ message: "Server error", extra: {} }, { status: 500 })),
    );

    renderAt("/my-assignments");

    expect(await screen.findByRole("alert")).toHaveTextContent(/couldn't load your assignments/i);
  });
});
