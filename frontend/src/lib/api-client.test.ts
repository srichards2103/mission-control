import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "@/testing/server";
import { api, clearTokens, getAccessToken, getRefreshToken, setTokens } from "./api-client";

// jsdom's window.location.assign is non-configurable, so it can't be spied on
// directly; stub the whole `location` object for the duration of a test.
function stubLocationAssign() {
  const originalLocation = window.location;
  const assign = vi.fn();
  Object.defineProperty(window, "location", {
    configurable: true,
    writable: true,
    value: { ...originalLocation, assign },
  });
  return {
    assign,
    restore: () => {
      Object.defineProperty(window, "location", { configurable: true, writable: true, value: originalLocation });
    },
  };
}

describe("token store", () => {
  it("keeps access in memory and refresh in localStorage", () => {
    setTokens("acc-1", "ref-1");
    expect(getAccessToken()).toBe("acc-1");
    expect(localStorage.getItem("mc_refresh")).toBe("ref-1");
    clearTokens();
    expect(getAccessToken()).toBeNull();
    expect(localStorage.getItem("mc_refresh")).toBeNull();
  });
});

describe("api interceptor", () => {
  beforeEach(() => {
    setTokens("expired-access", "valid-refresh");
  });

  afterEach(() => {
    clearTokens();
    vi.restoreAllMocks();
  });

  it("refreshes once on 401, retries the original request, and persists the rotated refresh token", async () => {
    let refreshCalls = 0;
    let protectedCalls = 0;

    server.use(
      http.post("/api/v1/auth/token/refresh/", async ({ request }) => {
        refreshCalls += 1;
        const body = (await request.json()) as { refresh: string };
        expect(body.refresh).toBe("valid-refresh");
        return HttpResponse.json({ access: "new-access", refresh: "rotated-refresh" });
      }),
      http.get("/api/v1/protected/", ({ request }) => {
        protectedCalls += 1;
        const auth = request.headers.get("authorization");
        if (auth === "Bearer expired-access") {
          return HttpResponse.json({ message: "Unauthorized", extra: {} }, { status: 401 });
        }
        expect(auth).toBe("Bearer new-access");
        return HttpResponse.json({ ok: true });
      }),
    );

    const { data } = await api.get("/protected/");

    expect(data).toEqual({ ok: true });
    expect(refreshCalls).toBe(1);
    expect(protectedCalls).toBe(2);
    expect(getAccessToken()).toBe("new-access");
    expect(localStorage.getItem("mc_refresh")).toBe("rotated-refresh");
  });

  it("dedupes concurrent 401s into a single refresh call", async () => {
    let refreshCalls = 0;

    server.use(
      http.post("/api/v1/auth/token/refresh/", async () => {
        refreshCalls += 1;
        return HttpResponse.json({ access: "new-access", refresh: "rotated-refresh" });
      }),
      http.get("/api/v1/protected/", ({ request }) => {
        const auth = request.headers.get("authorization");
        if (auth === "Bearer expired-access") {
          return HttpResponse.json({ message: "Unauthorized", extra: {} }, { status: 401 });
        }
        return HttpResponse.json({ ok: true });
      }),
    );

    const [first, second] = await Promise.all([api.get("/protected/"), api.get("/protected/")]);

    expect(first.data).toEqual({ ok: true });
    expect(second.data).toEqual({ ok: true });
    expect(refreshCalls).toBe(1);
  });

  it("clears tokens and redirects to /login when the refresh request itself fails", async () => {
    const { assign, restore } = stubLocationAssign();

    try {
      server.use(
        http.post("/api/v1/auth/token/refresh/", () =>
          HttpResponse.json({ message: "Unauthorized", extra: {} }, { status: 401 }),
        ),
        http.get("/api/v1/protected/", () =>
          HttpResponse.json({ message: "Unauthorized", extra: {} }, { status: 401 }),
        ),
      );

      await expect(api.get("/protected/")).rejects.toBeTruthy();

      expect(getAccessToken()).toBeNull();
      expect(localStorage.getItem("mc_refresh")).toBeNull();
      expect(assign).toHaveBeenCalledWith("/login");
    } finally {
      restore();
    }
  });

  it("clears tokens and redirects to /login when the refresh response body is malformed", async () => {
    const { assign, restore } = stubLocationAssign();

    try {
      server.use(
        // Malformed body: no `refresh` field, `access` is the wrong type.
        // Must not silently call setTokens(undefined, undefined) and carry on.
        http.post("/api/v1/auth/token/refresh/", () => HttpResponse.json({ access: 123 })),
        http.get("/api/v1/protected/", () =>
          HttpResponse.json({ message: "Unauthorized", extra: {} }, { status: 401 }),
        ),
      );

      await expect(api.get("/protected/")).rejects.toBeTruthy();

      expect(getAccessToken()).toBeNull();
      expect(localStorage.getItem("mc_refresh")).toBeNull();
      expect(assign).toHaveBeenCalledWith("/login");
    } finally {
      restore();
    }
  });

  it("does not attempt a refresh for a 401 coming from the auth/token endpoints", async () => {
    let refreshCalls = 0;

    server.use(
      http.post("/api/v1/auth/token/refresh/", () => {
        refreshCalls += 1;
        return HttpResponse.json({ access: "new-access", refresh: "rotated-refresh" });
      }),
      http.post("/api/v1/auth/token/", () =>
        HttpResponse.json({ message: "Validation error", extra: { fields: {} } }, { status: 401 }),
      ),
    );

    await expect(api.post("/auth/token/", { email: "x", password: "y" })).rejects.toBeTruthy();

    expect(refreshCalls).toBe(0);
    expect(getRefreshToken()).toBe("valid-refresh");
  });
});
