import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";

let accessToken: string | null = null;
const REFRESH_KEY = "mc_refresh";

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

export const api = axios.create({ baseURL: "/api/v1" });

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
      .post("/api/v1/auth/token/refresh/", { refresh })
      .then(({ data }) => {
        // Refresh-token rotation is ON server-side: every successful refresh
        // returns a NEW refresh token and blacklists the one just used, so it
        // must be persisted back to localStorage or the next refresh 401s.
        setTokens(data.access, data.refresh);
        return data.access as string;
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
      return api(original);
    } catch {
      clearTokens();
      window.location.assign("/login");
    }
  }
  throw error;
});
