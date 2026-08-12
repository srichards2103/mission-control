import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { RouterProvider } from "react-router-dom";
import { AppProvider } from "@/app/provider";
import { createRouter } from "@/app/router";
import { Toaster } from "@/components/ui/sonner";
import { leadUser, server } from "@/testing/mocks";

function renderAt(path: string) {
  render(
    <AppProvider>
      <RouterProvider router={createRouter([path])} />
      <Toaster />
    </AppProvider>,
  );
}

async function openCreateDialog() {
  await userEvent.click(await screen.findByRole("button", { name: /new mission/i }));
  return screen.findByRole("dialog");
}

async function fillRequiredFields(dialog: HTMLElement, opts: { name: string; start: string; end: string }) {
  await userEvent.type(within(dialog).getByLabelText(/^name$/i), opts.name);
  fireEvent.change(within(dialog).getByLabelText(/start date/i), { target: { value: opts.start } });
  fireEvent.change(within(dialog).getByLabelText(/end date/i), { target: { value: opts.end } });
}

describe("missions list", () => {
  it("lists missions and opens the create dialog", async () => {
    render(<AppProvider><RouterProvider router={createRouter(["/missions"])} /></AppProvider>);
    expect(await screen.findByText("Ganymede Survey")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /new mission/i }));
    expect(await screen.findByLabelText(/name/i)).toBeInTheDocument();
  });

  it("creates a mission and shows it in the list", async () => {
    renderAt("/missions");
    const dialog = await openCreateDialog();
    await fillRequiredFields(dialog, { name: "Io Relief Op", start: "2026-10-01", end: "2026-10-15" });
    await userEvent.click(within(dialog).getByRole("button", { name: /^create mission$/i }));

    // Proves the create mutation invalidated the list query: the new row shows up
    // without a manual refetch, alongside the pre-existing fixture row.
    expect(await screen.findByText("Io Relief Op")).toBeInTheDocument();
    expect(screen.getByText("Ganymede Survey")).toBeInTheDocument();
  });

  it("shows a validation error on the right field when creating a mission fails", async () => {
    server.use(
      http.post("/api/v1/missions/", () =>
        HttpResponse.json(
          {
            message: "Validation error",
            extra: { fields: { name: ["A mission with this name already exists."] } },
          },
          { status: 400 },
        ),
      ),
    );
    renderAt("/missions");
    const dialog = await openCreateDialog();
    await fillRequiredFields(dialog, { name: "Ganymede Survey", start: "2026-10-01", end: "2026-10-15" });
    await userEvent.click(within(dialog).getByRole("button", { name: /^create mission$/i }));

    // Field-level error lands under the name input...
    expect(await screen.findByText(/a mission with this name already exists/i)).toBeInTheDocument();
    // ...and the generic top-level message is toasted (no non_field_errors here, so
    // errorMessage() falls through to the plain "Validation error" string unchanged).
    expect(await screen.findByText(/^validation error$/i)).toBeInTheDocument();
  });

  it("surfaces the server's non-field validation message instead of a bare 'Validation error'", async () => {
    server.use(
      http.post("/api/v1/missions/", () =>
        HttpResponse.json(
          {
            message: "Validation error",
            extra: { fields: { non_field_errors: ["End date must be on or after the start date."] } },
          },
          { status: 400 },
        ),
      ),
    );
    renderAt("/missions");
    const dialog = await openCreateDialog();
    // Dates are ordered correctly here, so the client-side check does not intercept —
    // this exercises the server-returned non_field_errors path specifically.
    await fillRequiredFields(dialog, { name: "Deep Field Survey", start: "2026-10-01", end: "2026-10-15" });
    await userEvent.click(within(dialog).getByRole("button", { name: /^create mission$/i }));

    // Scoped to the dialog: the same text is also toasted outside it (and sonner
    // toasts can still be in the DOM from a still-timing-out toast in an earlier
    // test), so an unscoped query risks a false multiple-match or false positive.
    expect(await within(dialog).findByText(/end date must be on or after the start date/i)).toBeInTheDocument();
    // The bare fallback string must not be what's shown to the user in the dialog.
    expect(within(dialog).queryByText(/^validation error$/i)).not.toBeInTheDocument();
  });

  it("catches an obviously-invalid crew range before the round trip", async () => {
    renderAt("/missions");
    const dialog = await openCreateDialog();
    await fillRequiredFields(dialog, { name: "Backwards Mission", start: "2026-10-01", end: "2026-10-15" });
    fireEvent.change(within(dialog).getByLabelText(/min crew/i), { target: { value: "5" } });
    fireEvent.change(within(dialog).getByLabelText(/max crew/i), { target: { value: "2" } });
    await userEvent.click(within(dialog).getByRole("button", { name: /^create mission$/i }));

    expect(await screen.findByText(/max crew must be at least min crew/i)).toBeInTheDocument();
    // The dialog stayed open — no request needed to go out to catch this.
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("shows an error state instead of an empty table when the missions list fails to load", async () => {
    server.use(
      http.get("/api/v1/missions/", () =>
        HttpResponse.json({ message: "Server error", extra: {} }, { status: 500 }),
      ),
    );
    renderAt("/missions");
    expect(await screen.findByRole("alert")).toHaveTextContent(/couldn't load missions/i);
  });

  it("hides New mission for a user without mission.create", async () => {
    server.use(
      http.get("/api/v1/auth/me/", () =>
        HttpResponse.json({
          ...leadUser,
          permissions: leadUser.permissions.filter((p) => p !== "mission.create"),
        }),
      ),
    );
    renderAt("/missions");
    expect(await screen.findByText("Ganymede Survey")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /new mission/i })).not.toBeInTheDocument();
  });

  it("filters the list by status tab", async () => {
    renderAt("/missions");
    expect(await screen.findByText("Ganymede Survey")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("tab", { name: /^approved$/i }));
    expect(screen.queryByText("Ganymede Survey")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("tab", { name: /^draft$/i }));
    expect(await screen.findByText("Ganymede Survey")).toBeInTheDocument();
  });
});
