import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { AppProvider } from "@/app/provider";
import { createRouter } from "@/app/router";
import { RouterProvider } from "react-router-dom";
import { crewUser, server } from "@/testing/mocks";

function renderApp(path = "/") {
  const router = createRouter([path]);
  render(
    <AppProvider>
      <RouterProvider router={router} />
    </AppProvider>,
  );
}

describe("auth shell", () => {
  it("logs in and shows lead nav", async () => {
    renderApp("/login");
    await userEvent.type(await screen.findByLabelText(/email/i), "lead@helios.test");
    await userEvent.type(screen.getByLabelText(/password/i), "pw");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
    expect(await screen.findByRole("link", { name: /missions/i })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /settings/i })).not.toBeInTheDocument();
  });

  it("crew member is redirected from / to my-assignments", async () => {
    server.use(http.get("/api/v1/auth/me/", () => HttpResponse.json(crewUser)));
    renderApp("/");
    expect(await screen.findByRole("heading", { name: /my assignments/i })).toBeInTheDocument();
  });
});
