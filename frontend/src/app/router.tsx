import { createBrowserRouter, createMemoryRouter, Navigate } from "react-router-dom";
import { AppLayout } from "@/components/layout/app-layout";
import { ProtectedRoute, RequirePermission, hasPermission, useUser } from "@/lib/auth";
import { LoginForm } from "@/features/auth/components/login-form";
import { SettingsPage } from "@/features/settings/components/settings-page";
import { ProfilePage } from "@/features/profile/components/profile-page";
import { CrewListPage } from "@/features/crew/components/crew-list-page";
import { CrewDetailPage } from "@/features/crew/components/crew-detail-page";
import { MissionsPage } from "@/features/missions/components/missions-page";
import { MissionDetailPage } from "@/features/missions/components/mission-detail-page";

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
        {
          path: "/missions",
          element: (
            <RequirePermission permission="mission.view">
              <MissionsPage />
            </RequirePermission>
          ),
        },
        {
          path: "/missions/:missionId",
          element: (
            <RequirePermission permission="mission.view">
              <MissionDetailPage />
            </RequirePermission>
          ),
        },
        {
          path: "/crew",
          element: (
            <RequirePermission permission="crew.view">
              <CrewListPage />
            </RequirePermission>
          ),
        },
        {
          path: "/crew/:crewId",
          element: (
            <RequirePermission permission="crew.view">
              <CrewDetailPage />
            </RequirePermission>
          ),
        },
        { path: "/my-assignments", element: <h1>My Assignments</h1> }, // Stage 4
        {
          path: "/my-profile",
          element: (
            <RequirePermission permission="own_skills.edit">
              <ProfilePage />
            </RequirePermission>
          ),
        },
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
