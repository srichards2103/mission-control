import { render, screen } from "@testing-library/react";
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

describe("my-profile", () => {
  it("crew member edits and saves their profile", async () => {
    server.use(http.get("/api/v1/auth/me/", () => HttpResponse.json(crewUser)));
    let putBody: unknown = null;
    server.use(
      http.put("/api/v1/me/skills/", async ({ request }) => {
        putBody = await request.json();
        // Real backend returns the standard paginated envelope, not {"items": [...]}
        // as the brief's sample suggested — see profile/api/profile.ts for why.
        return HttpResponse.json({
          results: [{ skill_id: 1, skill_name: "Piloting", proficiency: 9 }],
          count: 1,
          limit: 25,
          offset: 0,
        });
      }),
    );
    renderAt("/my-profile");

    expect(await screen.findByText("Piloting")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /^save$/i }));

    expect(putBody).toEqual({ items: [{ skill_id: 1, proficiency: 8 }] });
    expect(await screen.findByText(/profile saved/i)).toBeInTheDocument();
  });

  it("adds and removes rows before saving, with proficiency kept in 1..10", async () => {
    server.use(http.get("/api/v1/auth/me/", () => HttpResponse.json(crewUser)));
    server.use(
      http.get("/api/v1/skills/", () =>
        HttpResponse.json({
          results: [
            { id: 1, name: "Piloting", description: "", is_archived: false },
            { id: 2, name: "Navigation", description: "", is_archived: false },
            { id: 3, name: "Retired Skill", description: "", is_archived: true },
          ],
          count: 3,
          limit: 25,
          offset: 0,
        }),
      ),
    );
    let putBody: unknown = null;
    server.use(
      http.put("/api/v1/me/skills/", async ({ request }) => {
        putBody = await request.json();
        return HttpResponse.json({ results: [], count: 0, limit: 25, offset: 0 });
      }),
    );
    renderAt("/my-profile");

    expect(await screen.findByText("Piloting")).toBeInTheDocument();

    // The archived skill must never be offered.
    expect(screen.queryByText("Retired Skill")).not.toBeInTheDocument();

    // Remove the only existing row.
    await userEvent.click(screen.getByRole("button", { name: /remove piloting/i }));
    expect(screen.queryByText("Piloting")).not.toBeInTheDocument();

    // Add a skill via the picker — it should default into range and be pickable only once.
    await userEvent.click(screen.getByRole("combobox", { name: /add a skill/i }));
    await userEvent.click(await screen.findByRole("option", { name: "Navigation" }));
    expect(await screen.findByText("Navigation")).toBeInTheDocument();
    // Now-chosen skill can't be picked again.
    await userEvent.click(screen.getByRole("combobox", { name: /add a skill/i }));
    expect(screen.queryByRole("option", { name: "Navigation" })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /^save$/i }));
    expect(putBody).toEqual({ items: [{ skill_id: 2, proficiency: 1 }] });
  });

  it("keeps the draft and surfaces the server message when saving fails", async () => {
    server.use(http.get("/api/v1/auth/me/", () => HttpResponse.json(crewUser)));
    server.use(
      http.put("/api/v1/me/skills/", () =>
        HttpResponse.json({ message: "Duplicate skill in submission.", extra: {} }, { status: 400 }),
      ),
    );
    renderAt("/my-profile");

    expect(await screen.findByText("Piloting")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /^save$/i }));

    expect(await screen.findByText(/duplicate skill in submission/i)).toBeInTheDocument();
    // The row the user had is still there, unlosable, ready to retry.
    expect(screen.getByText("Piloting")).toBeInTheDocument();
  });

  it("wipes the profile when every row is removed and saved", async () => {
    server.use(http.get("/api/v1/auth/me/", () => HttpResponse.json(crewUser)));
    let putBody: unknown = null;
    server.use(
      http.put("/api/v1/me/skills/", async ({ request }) => {
        putBody = await request.json();
        return HttpResponse.json({ results: [], count: 0, limit: 25, offset: 0 });
      }),
    );
    renderAt("/my-profile");

    expect(await screen.findByText("Piloting")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /remove piloting/i }));
    await userEvent.click(screen.getByRole("button", { name: /^save$/i }));

    // A save-success toast is already covered by the first test in this file; sonner
    // keeps a module-level toast queue that outlives each test's render, so repeatedly
    // asserting the same generic "Profile saved" text here would match stale toasts
    // from earlier tests in the file, not prove anything new. Assert on the request
    // and the resulting empty-profile UI state instead.
    expect(putBody).toEqual({ items: [] });
    expect(await screen.findByRole("combobox", { name: /add a skill/i })).toBeInTheDocument();
    expect(screen.queryByText("Piloting")).not.toBeInTheDocument();
  });

  it("surfaces a row-indexed validation error against the right row, not just a generic toast", async () => {
    server.use(http.get("/api/v1/auth/me/", () => HttpResponse.json(crewUser)));
    server.use(
      http.get("/api/v1/skills/", () =>
        HttpResponse.json({
          results: [
            { id: 1, name: "Piloting", description: "", is_archived: false },
            { id: 2, name: "Navigation", description: "", is_archived: false },
          ],
          count: 2,
          limit: 25,
          offset: 0,
        }),
      ),
    );
    server.use(
      // Exact shape captured live from PUT /api/v1/me/skills/: extra.fields is itself
      // keyed by stringified row index (the request body IS the items list, no
      // wrapping key) -- distinct from the requirements editor's extra.fields.items
      // shape. Row 1 (Navigation, the second row added below) is the one at fault.
      http.put("/api/v1/me/skills/", () =>
        HttpResponse.json(
          {
            message: "Validation error",
            extra: { fields: { "1": { proficiency: ["Ensure this value is less than or equal to 10."] } } },
          },
          { status: 400 },
        ),
      ),
    );
    renderAt("/my-profile");

    expect(await screen.findByText("Piloting")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("combobox", { name: /add a skill/i }));
    await userEvent.click(await screen.findByRole("option", { name: "Navigation" }));
    expect(await screen.findByText("Navigation")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /^save$/i }));

    const rowError = await screen.findByText(/ensure this value is less than or equal to 10/i);
    expect(rowError).toBeInTheDocument();
    // It's attached to Navigation's row (index 1), not Piloting's (index 0) -- the
    // point of row-level parsing over a bare toast.
    expect(rowError.closest("tr")).toHaveTextContent("Navigation");
    const pilotingRow = screen.getByText("Piloting").closest("tr");
    expect(pilotingRow).not.toHaveTextContent(/ensure this value/i);
    // The draft survives a failed save, same as the flat-error case above.
    expect(screen.getByText("Piloting")).toBeInTheDocument();
  });

  it("shows an error state instead of an empty profile when it fails to load", async () => {
    server.use(http.get("/api/v1/auth/me/", () => HttpResponse.json(crewUser)));
    server.use(
      http.get("/api/v1/me/skills/", () =>
        HttpResponse.json({ message: "Server error", extra: {} }, { status: 500 }),
      ),
    );
    renderAt("/my-profile");

    expect(await screen.findByRole("alert")).toHaveTextContent(/couldn't load your profile/i);
  });
});
