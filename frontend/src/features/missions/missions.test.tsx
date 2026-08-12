import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { RouterProvider } from "react-router-dom";
import { AppProvider } from "@/app/provider";
import { createRouter } from "@/app/router";

describe("missions list", () => {
  it("lists missions and opens the create dialog", async () => {
    render(<AppProvider><RouterProvider router={createRouter(["/missions"])} /></AppProvider>);
    expect(await screen.findByText("Ganymede Survey")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /new mission/i }));
    expect(await screen.findByLabelText(/name/i)).toBeInTheDocument();
  });
});
