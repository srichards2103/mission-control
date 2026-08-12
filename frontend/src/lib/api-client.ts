import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
import { z } from "zod";

let accessToken: string | null = null;
const REFRESH_KEY = "mc_refresh";
const API_V1_BASE = "/api/v1";

// Shared shape of every endpoint that hands back a fresh token pair (login, refresh).
// Was defined independently here and in features/auth/api/auth.ts; hoisted so the two
// can't drift.
export const TokenPairSchema = z.object({ access: z.string(), refresh: z.string() });

export function setTokens(access: string, refresh: string) {
  accessToken = access;
  localStorage.setItem(REFRESH_KEY, refresh);
}
export function clearTokens() {
  accessToken = null;
  localStorage.removeItem(REFRESH_KEY);
}
export function getAccessToken() {
  return accessToken;
}
export function getRefreshToken() {
  return localStorage.getItem(REFRESH_KEY);
}

export const api = axios.create({ baseURL: API_V1_BASE });

api.interceptors.request.use((config) => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`;
  return config;
});

type RetriableRequestConfig = InternalAxiosRequestConfig & { _retried?: boolean };

// Ensures concurrent 401s share a single in-flight refresh instead of each
// firing their own POST /auth/token/refresh/ (which would race the rotated
// refresh token and blacklist itself).
let refreshPromise: Promise<string> | null = null;

async function refreshAccessToken(refresh: string): Promise<string> {
  if (!refreshPromise) {
    refreshPromise = axios
      .post(`${API_V1_BASE}/auth/token/refresh/`, { refresh })
      .then(({ data }) => {
        // Parse before trusting the body: a malformed response (proxy error
        // page, renamed field) must throw here rather than silently calling
        // setTokens(undefined, undefined), which would leave every later
        // request going out unauthenticated with no error surfaced anywhere.
        const parsed = TokenPairSchema.parse(data);
        // Refresh-token rotation is ON server-side: every successful refresh
        // returns a NEW refresh token and blacklists the one just used, so it
        // must be persisted back to localStorage or the next refresh 401s.
        setTokens(parsed.access, parsed.refresh);
        return parsed.access;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

api.interceptors.response.use(undefined, async (error: AxiosError) => {
  const original = error.config as RetriableRequestConfig | undefined;
  const refresh = getRefreshToken();
  if (
    error.response?.status === 401 &&
    original &&
    refresh &&
    !original._retried &&
    !original.url?.includes("/auth/token")
  ) {
    original._retried = true;
    try {
      await refreshAccessToken(refresh);
    } catch {
      // The refresh itself failed (expired/blacklisted refresh token, network error,
      // malformed body) -- "refresh once, then log out" applies unconditionally here.
      clearTokens();
      window.location.assign("/login");
      throw error;
    }
    try {
      return await api(original);
    } catch (retryErr) {
      // The refresh succeeded but the retried request still failed. Only force a
      // logout if it failed with another 401 (a still-bad session) -- an unrelated
      // 404/500/network error on the retried request must propagate as-is, not bounce
      // the user to /login.
      if (retryErr instanceof AxiosError && retryErr.response?.status === 401) {
        clearTokens();
        window.location.assign("/login");
      }
      throw retryErr;
    }
  }
  throw error;
});
