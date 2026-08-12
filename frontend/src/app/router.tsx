import { createBrowserRouter, createMemoryRouter, Navigate } from "react-router-dom";
import { AppLayout } from "@/components/layout/app-layout";
import { ProtectedRoute, RequirePermission, hasPermission, useUser } from "@/lib/auth";
import { LoginForm } from "@/features/auth/components/login-form";
import { SettingsPage } from "@/features/settings/components/settings-page";

function HomeRedirect() {
  const { data: user } = useUser();
  if (!user) return null;
  if (!hasPermission(user, "dashboard.view")) return <Navigate to="/my-assignments" replace />;
  return <h1 className="text-xl font-semibold">Dashboard</h1>; // replaced in Stage 6
}

const routes = [
  { path: "/login", element: <LoginForm /> },
  {
    element: <ProtectedRoute />,
    children: [{
      element: <AppLayout />,
      children: [
        { path: "/", element: <HomeRedirect /> },
        { path: "/missions", element: <h1>Missions</h1> },          // Stage 3
        { path: "/crew", element: <h1>Crew</h1> },                  // Stage 2
        { path: "/my-assignments", element: <h1>My Assignments</h1> }, // Stage 4
        { path: "/my-profile", element: <h1>My Profile</h1> },      // Stage 2
        {
          path: "/settings",
          element: (
            <RequirePermission permission="settings.view">
              <SettingsPage />
            </RequirePermission>
          ),
        },
      ],
    }],
  },
];

export function createRouter(initialEntries?: string[]) {
  return initialEntries
    ? createMemoryRouter(routes, { initialEntries })
    : createBrowserRouter(routes);
}
