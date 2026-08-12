import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { http, HttpResponse, delay } from "msw";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { server } from "@/testing/server";
import { directorUser } from "@/testing/mocks";
import { RequirePermission } from "./auth";

function renderWithPermission(permission: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/protected"]}>
        <Routes>
          <Route path="/" element={<div>Home</div>} />
          <Route
            path="/protected"
            element={
              <RequirePermission permission={permission}>
                <div>Secret content</div>
              </RequirePermission>
            }
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

// F7: RequirePermission had no isLoading guard, so hasPermission(undefined, perm) --
// which is unconditionally false while useUser() is still in flight -- would bounce
// even a permitted user to "/" for the split second before the query settles. Every
// current usage happens to be nested under a resolved ProtectedRoute so this never
// fired in practice, but the component wasn't safe to use standalone. This test
// exercises RequirePermission directly (not nested under ProtectedRoute) so the guard
// is what's actually being proven, not incidental protection from the wrapper.
describe("RequirePermission", () => {
  it("renders nothing (not the redirect) while the permission check is still loading, then the content once it resolves true", async () => {
    server.use(
      http.get("/api/v1/auth/me/", async () => {
        await delay(50);
        return HttpResponse.json(directorUser);
      }),
    );
    renderWithPermission("settings.manage");

    // Mid-flight: neither the redirect target nor the gated content should be visible.
    expect(screen.queryByText("Home")).not.toBeInTheDocument();
    expect(screen.queryByText("Secret content")).not.toBeInTheDocument();

    expect(await screen.findByText("Secret content")).toBeInTheDocument();
  });

  it("still redirects once loading settles and the user lacks the permission", async () => {
    server.use(http.get("/api/v1/auth/me/", () => HttpResponse.json(directorUser)));
    renderWithPermission("nonexistent.permission");

    expect(await screen.findByText("Home")).toBeInTheDocument();
    expect(screen.queryByText("Secret content")).not.toBeInTheDocument();
  });
});
