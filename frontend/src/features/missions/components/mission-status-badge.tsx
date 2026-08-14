import { StatusDot, type StatusDotColor } from "@/components/ui/status-dot";
import type { MissionStatus } from "@/features/missions/api/missions";

export const MISSION_STATUS_LABELS: Record<MissionStatus, string> = {
  draft: "Draft",
  pending_approval: "Pending Approval",
  approved: "Approved",
  active: "Active",
  completed: "Completed",
  rejected: "Rejected",
  cancelled: "Cancelled",
};

// The FSM's two terminal statuses -- no further transition is possible from either.
// Single canonical definition; previously duplicated in transition-buttons.tsx,
// staffing-panel.tsx, and my-assignments-page.tsx (the last as a differently-named
// Set). Import this rather than re-declaring it a fourth time.
export const TERMINAL_MISSION_STATUSES: readonly MissionStatus[] = ["completed", "cancelled"];

// Statuses render as a colored dot + text (see StatusDot), not filled pills.
const STATUS_DOTS: Record<MissionStatus, { color: StatusDotColor; muted?: boolean }> = {
  draft: { color: "gray" },
  pending_approval: { color: "amber" },
  approved: { color: "blue" },
  active: { color: "green" },
  completed: { color: "purple" },
  rejected: { color: "red" },
  cancelled: { color: "gray", muted: true },
};

export function MissionStatusBadge({ status }: { status: MissionStatus }) {
  const dot = STATUS_DOTS[status];
  return (
    <StatusDot color={dot.color} muted={dot.muted}>
      {MISSION_STATUS_LABELS[status]}
    </StatusDot>
  );
}
