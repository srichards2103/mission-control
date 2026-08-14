import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { SectionLabel } from "@/components/ui/page-header";
import { StatusDot, type StatusDotColor } from "@/components/ui/status-dot";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { useRemoveAssignment, useStaffing } from "@/features/assignments/api/assignments";
import { AddCrewDialog } from "@/features/assignments/components/add-crew-dialog";
import { MatchDialog } from "@/features/matching/components/match-dialog";
import { useMission } from "@/features/missions/api/missions";
import { TERMINAL_MISSION_STATUSES } from "@/features/missions/components/mission-status-badge";
import { errorMessage } from "@/lib/api-errors";
import { hasPermission, useUser } from "@/lib/auth";

const ASSIGNMENT_DOTS: Record<string, { color: StatusDotColor; muted?: boolean }> = {
  proposed: { color: "amber" },
  accepted: { color: "green" },
  declined: { color: "red" },
  removed: { color: "gray", muted: true },
};

export function StaffingPanel({ missionId }: { missionId: number }) {
  const { data: user } = useUser();
  const { data: staffing, isLoading, isError } = useStaffing(missionId);
  // Same query key as the mission-detail page's own useMission(id) -- by the time
  // this panel mounts the page has already loaded it, so this is a cache hit, not a
  // second network round trip. Needed here only to gate the Auto-match button on
  // "mission isn't terminal" without threading mission status through as a prop.
  const { data: mission } = useMission(missionId);
  const removeAssignment = useRemoveAssignment(missionId);
  const [addCrewOpen, setAddCrewOpen] = useState(false);
  const [matchOpen, setMatchOpen] = useState(false);
  // Tracks which single roster row is mid-removal, so an in-flight removal only
  // disables that row's own Remove button rather than every row's (removeAssignment
  // is one shared mutation object for the whole panel; isPending alone can't tell
  // rows apart).
  const [removingId, setRemovingId] = useState<number | null>(null);
  const canManage = hasPermission(user, "assignment.manage");
  const canMatch =
    hasPermission(user, "match.run") && !!mission && !TERMINAL_MISSION_STATUSES.includes(mission.status);

  // isLoading -> isError -> data, in that order (see mission-detail-page.tsx and
  // others): data?.map must never run before both checks.
  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading staffing…</p>;
  }
  if (isError || !staffing) {
    return (
      <p role="alert" className="text-sm text-destructive">
        Couldn&apos;t load staffing. Please try again.
      </p>
    );
  }

  async function handleRemove(assignmentId: number) {
    setRemovingId(assignmentId);
    try {
      await removeAssignment.mutateAsync(assignmentId);
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setRemovingId(null);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-3">
        <p className="num text-sm text-muted-foreground">
          Crew {staffing.accepted_count}/{staffing.min_crew}
          {staffing.max_crew !== staffing.min_crew ? `–${staffing.max_crew}` : ""} ·{" "}
          {staffing.fully_covered ? "Fully covered" : "Not fully covered"}
        </p>
        {staffing.requirements.length === 0 ? (
          <p className="text-sm text-muted-foreground">No requirements set.</p>
        ) : (
          staffing.requirements.map((req) => {
            const pct =
              req.required_count > 0 ? Math.min(100, (req.filled_count / req.required_count) * 100) : 100;
            return (
              <div key={req.requirement_id} className="flex flex-col gap-1">
                <span className="num text-sm">
                  {req.skill_name} ≥{req.min_proficiency} · {req.filled_count}/{req.required_count}
                </span>
                <div className="h-1 w-full overflow-hidden rounded-full bg-muted" role="progressbar" aria-valuenow={pct}>
                  <div className="h-full rounded-full bg-emerald-500" style={{ width: `${pct}%` }} />
                </div>
                <p className="text-xs text-muted-foreground">
                  {req.filled_by.length > 0
                    ? `Filled by ${req.filled_by.map((f) => f.name).join(", ")}`
                    : "No one filling this requirement yet."}
                </p>
              </div>
            );
          })
        )}
      </div>

      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <SectionLabel>Roster</SectionLabel>
          <div className="flex gap-2">
            {canMatch && (
              <Button size="sm" variant="outline" onClick={() => setMatchOpen(true)}>
                Auto-match
              </Button>
            )}
            {canManage && (
              <Button size="sm" onClick={() => setAddCrewOpen(true)}>
                Add crew
              </Button>
            )}
          </div>
        </div>
        {staffing.roster.length === 0 ? (
          <p className="text-sm text-muted-foreground">No crew proposed yet.</p>
        ) : (
          <ul className="flex flex-col border-y" aria-label="Roster">
            {staffing.roster.map((entry) => (
              <li
                key={entry.assignment_id}
                className="group/row flex h-[38px] flex-wrap items-center gap-3 border-b text-sm last:border-0"
              >
                <span className="font-medium">{entry.name}</span>
                <StatusDot
                  color={ASSIGNMENT_DOTS[entry.status]?.color ?? "gray"}
                  muted={ASSIGNMENT_DOTS[entry.status]?.muted}
                  className="capitalize"
                >
                  {entry.status}
                </StatusDot>
                {/* Soft conflict: overlapping but non-blocking commitment elsewhere — a
                    warning, surfaced via popover, never disables anything. */}
                {entry.soft_conflicts.length > 0 && (
                  <Popover>
                    <PopoverTrigger className="cursor-pointer">
                      <StatusDot color="amber" className="text-amber-600">Conflict</StatusDot>
                    </PopoverTrigger>
                    <PopoverContent>
                      <ul className="flex flex-col gap-1 text-xs">
                        {entry.soft_conflicts.map((conflict, index) => (
                          <li key={index}>
                            {conflict.mission_name} ({conflict.mission_status}, {conflict.assignment_status})
                          </li>
                        ))}
                      </ul>
                    </PopoverContent>
                  </Popover>
                )}
                {/* Hard block: an accepted assignment on an approved/active mission with
                    overlapping dates — the one that actually blocks proposing this
                    person (the server refuses that with a 400). */}
                {entry.hard_blocked && <StatusDot color="red" className="text-destructive">Unavailable</StatusDot>}
                {canManage && (
                  <Button
                    size="sm"
                    variant="ghost"
                    className="ml-auto opacity-0 transition-opacity group-hover/row:opacity-100 focus-visible:opacity-100"
                    aria-label={`Remove ${entry.name}`}
                    disabled={removingId === entry.assignment_id}
                    onClick={() => handleRemove(entry.assignment_id)}
                  >
                    Remove
                  </Button>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {canManage && (
        <AddCrewDialog
          missionId={missionId}
          open={addCrewOpen}
          onOpenChange={setAddCrewOpen}
          currentRosterUserIds={staffing.roster.map((r) => r.user_id)}
        />
      )}
      {canMatch && <MatchDialog missionId={missionId} open={matchOpen} onOpenChange={setMatchOpen} />}
    </div>
  );
}
