import { NavLink, Outlet } from "react-router-dom";
import { hasPermission, useLogout, useUser } from "@/lib/auth";
import { cn } from "@/lib/utils";

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
    <div className="h-svh">
      {/* Fixed 220px sidebar; the main column scrolls independently. */}
      <aside className="fixed inset-y-0 left-0 flex w-[220px] flex-col gap-0.5 border-r bg-sidebar px-3 py-4">
        <div className="mb-4 px-2 text-sm font-semibold">{user?.tenant.name}</div>
        {NAV.filter((n) => hasPermission(user, n.perm)).map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            className={({ isActive }) =>
              cn(
                "rounded-md px-2 py-1 text-sm text-sidebar-foreground/70 transition-colors hover:bg-sidebar-accent hover:text-sidebar-foreground",
                isActive && "bg-sidebar-accent font-medium text-sidebar-foreground",
              )
            }
          >
            {n.label}
          </NavLink>
        ))}
        <button
          onClick={logout}
          className="mt-auto rounded-md px-2 py-1 text-left text-xs text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-foreground"
        >
          Sign out · {user?.name}
        </button>
      </aside>
      <main className="ml-[220px] h-full overflow-y-auto">
        <div className="px-8 py-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
