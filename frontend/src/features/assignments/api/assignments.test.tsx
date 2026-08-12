import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "@/testing/server";
import { useRespondAssignment } from "./assignments";

function wrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

// F6: accepting/declining changes accepted_count, fully_covered, and the roster
// entry's status on the mission's staffing -- exactly what invalidateStaffing()
// (shared with propose/remove) invalidates. useRespondAssignment used to invalidate
// only the my-assignments list, leaving a mission-detail/staffing-panel view stale
// after a respond. The router never co-mounts those two screens today, so this is a
// cache-level test rather than a rendered-component one -- it's the only way to prove
// the invalidation happens without depending on that routing coincidence staying true.
describe("useRespondAssignment", () => {
  it("invalidates the mission's staffing caches (via mission.id from the response), not just my-assignments", async () => {
    const missionId = 42;
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    queryClient.setQueryData(["missions", missionId, "staffing"], { fake: "stale-staffing" });
    queryClient.setQueryData(["missions", missionId], { fake: "stale-mission" });
    queryClient.setQueryData(["me", "assignments"], { fake: "stale-my-assignments" });

    server.use(
      http.post("/api/v1/assignments/7/respond/", () =>
        HttpResponse.json({
          id: 7,
          status: "accepted",
          decline_reason: "",
          responded_at: "2026-08-11T00:00:00Z",
          mission: {
            id: missionId,
            name: "Ganymede Survey",
            status: "approved",
            start_date: "2026-09-01",
            end_date: "2026-09-30",
            description: "",
          },
        }),
      ),
    );

    const { result } = renderHook(() => useRespondAssignment(), { wrapper: wrapper(queryClient) });

    await result.current.mutateAsync({ assignmentId: 7, action: "accept" });

    await waitFor(() => {
      expect(queryClient.getQueryState(["missions", missionId, "staffing"])?.isInvalidated).toBe(true);
      expect(queryClient.getQueryState(["missions", missionId])?.isInvalidated).toBe(true);
      expect(queryClient.getQueryState(["me", "assignments"])?.isInvalidated).toBe(true);
    });
  });

  it("does not touch another mission's staffing cache", async () => {
    const missionId = 42;
    const otherMissionId = 99;
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    queryClient.setQueryData(["missions", missionId, "staffing"], { fake: "target" });
    queryClient.setQueryData(["missions", otherMissionId, "staffing"], { fake: "unrelated" });

    server.use(
      http.post("/api/v1/assignments/7/respond/", () =>
        HttpResponse.json({
          id: 7,
          status: "declined",
          decline_reason: "",
          responded_at: "2026-08-11T00:00:00Z",
          mission: {
            id: missionId,
            name: "Ganymede Survey",
            status: "approved",
            start_date: "2026-09-01",
            end_date: "2026-09-30",
            description: "",
          },
        }),
      ),
    );

    const { result } = renderHook(() => useRespondAssignment(), { wrapper: wrapper(queryClient) });
    await result.current.mutateAsync({ assignmentId: 7, action: "decline" });

    await waitFor(() => {
      expect(queryClient.getQueryState(["missions", missionId, "staffing"])?.isInvalidated).toBe(true);
    });
    expect(queryClient.getQueryState(["missions", otherMissionId, "staffing"])?.isInvalidated).toBeFalsy();
  });
});
