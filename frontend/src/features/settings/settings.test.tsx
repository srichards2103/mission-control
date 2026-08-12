import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { RouterProvider } from "react-router-dom";
import { AppProvider } from "@/app/provider";
import { createRouter } from "@/app/router";
import { Toaster } from "@/components/ui/sonner";
import { crewUser, directorUser, server } from "@/testing/mocks";

function renderAt(path: string) {
  render(
    <AppProvider>
      <RouterProvider router={createRouter([path])} />
      <Toaster />
    </AppProvider>,
  );
}

describe("settings", () => {
  it("crew member is bounced away from settings", async () => {
    server.use(http.get("/api/v1/auth/me/", () => HttpResponse.json(crewUser)));
    renderAt("/settings");
    expect(await screen.findByRole("heading", { name: /my assignments/i })).toBeInTheDocument();
  });

  it("director sees tabs and creates a skill", async () => {
    server.use(http.get("/api/v1/auth/me/", () => HttpResponse.json(directorUser)));
    renderAt("/settings");
    await userEvent.click(await screen.findByRole("tab", { name: /skills/i }));
    expect(await screen.findByText("Piloting")).toBeInTheDocument();
    await userEvent.type(screen.getByPlaceholderText(/new skill name/i), "EVA Ops");
    await userEvent.click(screen.getByRole("button", { name: /add skill/i }));
    expect(await screen.findByText("EVA Ops")).toBeInTheDocument();
  });

  it("shows a validation error on the right field when adding a user fails", async () => {
    server.use(http.get("/api/v1/auth/me/", () => HttpResponse.json(directorUser)));
    server.use(
      http.post("/api/v1/settings/users/", () =>
        HttpResponse.json(
          { message: "Validation error", extra: { fields: { email: ["Email already in use."] } } },
          { status: 400 },
        ),
      ),
    );
    renderAt("/settings");

    await userEvent.click(await screen.findByRole("button", { name: /add user/i }));
    const dialog = await screen.findByRole("dialog");
    await userEvent.type(within(dialog).getByLabelText(/^name$/i), "New Person");
    await userEvent.type(within(dialog).getByLabelText(/^email$/i), "dup@helios.test");
    await userEvent.type(within(dialog).getByLabelText(/^password$/i), "password123");
    await userEvent.click(within(dialog).getByRole("button", { name: /add user/i }));

    // Field-level error lands under the email input...
    expect(await screen.findByText(/email already in use/i)).toBeInTheDocument();
    // ...and the top-level message is toasted.
    expect(await screen.findByText(/^validation error$/i)).toBeInTheDocument();
  });

  it("shows the server's business-rule message when a director deactivates themselves", async () => {
    server.use(http.get("/api/v1/auth/me/", () => HttpResponse.json(directorUser)));
    server.use(
      http.patch("/api/v1/settings/users/:id/", () =>
        HttpResponse.json({ message: "You cannot modify your own account.", extra: {} }, { status: 400 }),
      ),
    );
    renderAt("/settings");

    await userEvent.click(await screen.findByRole("button", { name: /deactivate/i }));

    expect(await screen.findByText(/you cannot modify your own account/i)).toBeInTheDocument();
  });

  it("shows an error state instead of an empty table when the skills list fails to load", async () => {
    server.use(http.get("/api/v1/auth/me/", () => HttpResponse.json(directorUser)));
    server.use(
      http.get("/api/v1/skills/", () =>
        HttpResponse.json({ message: "Server error", extra: {} }, { status: 500 }),
      ),
    );
    renderAt("/settings");

    await userEvent.click(await screen.findByRole("tab", { name: /skills/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/couldn't load skills/i);
  });

  it("director views and renames the organisation", async () => {
    server.use(http.get("/api/v1/auth/me/", () => HttpResponse.json(directorUser)));
    // Override GET too (not just PATCH) so the post-save refetch reflects the
    // rename — the base handler in mocks.ts always returns "Helios".
    let orgName = "Helios";
    server.use(
      http.get("/api/v1/settings/organisation/", () =>
        HttpResponse.json({ id: 1, name: orgName, slug: "helios" }),
      ),
      http.patch("/api/v1/settings/organisation/", async ({ request }) => {
        const body = (await request.json()) as { name: string };
        orgName = body.name;
        return HttpResponse.json({ id: 1, name: orgName, slug: "helios" });
      }),
    );
    renderAt("/settings");

    // Scoped to <main>: the sidebar also shows the tenant name "Helios", which
    // would otherwise collide with the organisation tab's own "Helios" text.
    const main = await screen.findByRole("main");
    await userEvent.click(await within(main).findByRole("tab", { name: /organisation/i }));
    expect(await within(main).findByText("Helios")).toBeInTheDocument();

    await userEvent.click(within(main).getByRole("button", { name: /edit organisation name/i }));
    const input = within(main).getByLabelText(/organisation name/i);
    await userEvent.clear(input);
    await userEvent.type(input, "Helios Corp");
    await userEvent.click(within(main).getByRole("button", { name: /^save$/i }));

    expect(await within(main).findByText("Helios Corp")).toBeInTheDocument();
  });
});
