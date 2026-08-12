import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { RouterProvider } from "react-router-dom";
import { AppProvider } from "@/app/provider";
import { createRouter } from "@/app/router";
import { crewUser, dashboardFixture, server } from "@/testing/mocks";

function renderAt(path: string) {
  render(
    <AppProvider>
      <RouterProvider router={createRouter([path])} />
    </AppProvider>,
  );
}

describe("dashboard page", () => {
  it("renders the mocked payload: a status chip, an at-risk mission name, org utilization %, and a gap row", async () => {
    renderAt("/");

    expect(await screen.findByText(/pending approval: 1/i)).toBeInTheDocument();
    expect(await screen.findByText("Ganymede Survey")).toBeInTheDocument();
    expect(screen.getByText(/at risk/i)).toBeInTheDocument();
    expect(screen.getByText("42%")).toBeInTheDocument();
    expect(screen.getByText("Piloting")).toBeInTheDocument();
    expect(screen.getByText(/^gap$/i)).toBeInTheDocument();
  });

  it("shows an error state when the dashboard fails to load", async () => {
    server.use(
      http.get("/api/v1/dashboard/", () =>
        HttpResponse.json({ message: "Server error", extra: {} }, { status: 500 })),
    );
    renderAt("/");
    expect(await screen.findByRole("alert")).toHaveTextContent(/couldn't load the dashboard/i);
  });

  it("redirects a crew member (no dashboard.view) away from the dashboard to their assignments", async () => {
    server.use(http.get("/api/v1/auth/me/", () => HttpResponse.json(crewUser)));
    renderAt("/");
    expect(await screen.findByRole("heading", { name: /my assignments/i })).toBeInTheDocument();
  });

  it("renders sensibly for an empty organisation instead of a wall of unlabeled zeros", async () => {
    server.use(
      http.get("/api/v1/dashboard/", () =>
        HttpResponse.json({
          pipeline: {
            status_counts: {
              draft: 0, pending_approval: 0, approved: 0, rejected: 0,
              active: 0, completed: 0, cancelled: 0,
            },
            pending_approvals: [],
            upcoming: [],
          },
          readiness: [],
          utilization: { window_days: 90, org_utilization_pct: 0, crew: [] },
          skill_gaps: [],
        }),
      ),
    );
    renderAt("/");
    expect(await screen.findByText(/nothing is awaiting approval/i)).toBeInTheDocument();
    expect(screen.getByText(/no live missions need staffing/i)).toBeInTheDocument();
    expect(screen.getByText(/no active crew members/i)).toBeInTheDocument();
    expect(screen.getByText(/no open missions currently need skills/i)).toBeInTheDocument();
  });
});

// Guards the fixture itself stays representative of what the assertions above lean on.
it("fixture sanity: dashboardFixture has an at-risk readiness row and a skill gap", () => {
  expect(dashboardFixture.readiness.some((r) => r.at_risk)).toBe(true);
  expect(dashboardFixture.skill_gaps.some((g) => g.gap)).toBe(true);
});
