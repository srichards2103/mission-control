import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { RouterProvider } from "react-router-dom";
import { AppProvider } from "@/app/provider";
import { createRouter } from "@/app/router";
import { crewUser, directorUser, server } from "@/testing/mocks";

function renderAt(path: string) {
  render(<AppProvider><RouterProvider router={createRouter([path])} /></AppProvider>);
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
});
