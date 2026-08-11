import { NavLink, Outlet } from "react-router-dom";
import { hasPermission, useLogout, useUser } from "@/lib/auth";

const NAV = [
  { to: "/", label: "Dashboard", perm: "dashboard.view" },
  { to: "/missions", label: "Missions", perm: "mission.view" },
  { to: "/crew", label: "Crew", perm: "crew.view" },
  { to: "/my-assignments", label: "My Assignments", perm: "assignment.respond" },
  { to: "/my-profile", label: "My Profile", perm: "own_skills.edit" },
  { to: "/settings", label: "Settings", perm: "settings.view" },
];

export function AppLayout() {
  const { data: user } = useUser();
  const logout = useLogout();
  return (
    <div className="flex min-h-screen">
      <aside className="w-56 border-r p-4 flex flex-col gap-1">
        <div className="font-semibold mb-4">{user?.tenant.name}</div>
        {NAV.filter((n) => hasPermission(user, n.perm)).map((n) => (
          <NavLink key={n.to} to={n.to} className="rounded px-2 py-1 text-sm hover:bg-accent">
            {n.label}
          </NavLink>
        ))}
        <button onClick={logout} className="mt-auto text-left text-sm text-muted-foreground px-2">
          Sign out · {user?.name}
        </button>
      </aside>
      <main className="flex-1 p-6">
        <Outlet />
      </main>
    </div>
  );
}
