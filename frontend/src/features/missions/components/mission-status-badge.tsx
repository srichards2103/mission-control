import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
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

// Badge has no amber/blue/green variant, so those three statuses reuse the
// "outline" variant and layer color utility classes on top.
const STATUS_STYLES: Record<
  MissionStatus,
  { variant: "default" | "secondary" | "destructive" | "outline"; className?: string }
> = {
  draft: { variant: "secondary" },
  pending_approval: {
    variant: "outline",
    className: "border-amber-300 bg-amber-100 text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-300",
  },
  approved: {
    variant: "outline",
    className: "border-blue-300 bg-blue-100 text-blue-900 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-300",
  },
  active: {
    variant: "outline",
    className: "border-green-300 bg-green-100 text-green-900 dark:border-green-800 dark:bg-green-950 dark:text-green-300",
  },
  completed: { variant: "default" },
  rejected: { variant: "destructive" },
  cancelled: { variant: "outline", className: "text-muted-foreground" },
};

export function MissionStatusBadge({ status }: { status: MissionStatus }) {
  const style = STATUS_STYLES[status];
  return (
    <Badge variant={style.variant} className={cn(style.className)}>
      {MISSION_STATUS_LABELS[status]}
    </Badge>
  );
}
