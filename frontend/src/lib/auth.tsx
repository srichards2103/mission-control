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

export function RequirePermission({ permission, children }: { permission: string; children: React.ReactNode }) {
  const { data: user } = useUser();
  if (!hasPermission(user, permission)) return <Navigate to="/" replace />;
  return <>{children}</>;
}
