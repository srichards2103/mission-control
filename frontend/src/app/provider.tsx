import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

export function AppProvider({ children }: { children: React.ReactNode }) {
  // Created per-mount (not at module scope) so each app instance — and each
  // test render — gets an isolated cache. A module-scoped singleton would
  // leak query data across renders (e.g. a stale /auth/me/ result served to
  // a different logged-in user in tests, or across React strict-mode remounts).
  const [queryClient] = useState(() => new QueryClient({ defaultOptions: { queries: { retry: false } } }));
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
