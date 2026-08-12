import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Navigate, Outlet } from "react-router-dom";
import { fetchMe, type User } from "@/features/auth/api/auth";
import { clearTokens } from "@/lib/api-client";

export function useUser() {
  return useQuery({ queryKey: ["auth", "me"], queryFn: fetchMe, retry: false, staleTime: 5 * 60_000 });
}

export function useLogout() {
  const qc = useQueryClient();
  return () => {
    clearTokens();
    qc.clear();
    window.location.assign("/login");
  };
}

export function hasPermission(user: User | undefined, perm: string) {
  return !!user?.permissions.includes(perm);
}

export function ProtectedRoute() {
  const { data: user, isLoading, isError } = useUser();
  if (isLoading) return null;
  if (isError || !user) return <Navigate to="/login" replace />;
  return <Outlet />;
}

// Invariant this component relies on: it must only be rendered under a resolved
// ProtectedRoute (i.e. useUser() has already settled, successfully, higher up the
// tree). Without the isLoading guard below, hasPermission(undefined, perm) is false
// while the query is still in flight, which would bounce a permitted user to "/" for
// the split second before `user` loads -- every current usage happens to be safely
// nested under ProtectedRoute, but nothing enforces that for a future standalone use
// (e.g. inside a modal, or a route outside that tree). Guard it here so this component
// is safe on its own rather than merely safe by convention.
export function RequirePermission({ permission, children }: { permission: string; children: React.ReactNode }) {
  const { data: user, isLoading } = useUser();
  if (isLoading) return null;
  if (!hasPermission(user, permission)) return <Navigate to="/" replace />;
  return <>{children}</>;
}
