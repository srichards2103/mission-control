import { useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { useRemoveAssignment, useStaffing } from "@/features/assignments/api/assignments";
import { AddCrewDialog } from "@/features/assignments/components/add-crew-dialog";
import { MatchDialog } from "@/features/matching/components/match-dialog";
import { useMission, type MissionStatus } from "@/features/missions/api/missions";
import { errorMessage } from "@/lib/api-errors";
import { hasPermission, useUser } from "@/lib/auth";

// Mirrors transition-buttons.tsx's TERMINAL_STATUSES -- duplicated rather than
// imported because that constant isn't exported, and this is the only other place
// that needs "is this mission over" as a plain gate (not the FSM's full transition
// table). Auto-matching a completed/cancelled mission is refused server-side with a
// 400 ("Cannot match a completed or cancelled mission."), so this only avoids
// showing a button that would always fail.
const TERMINAL_STATUSES: MissionStatus[] = ["completed", "cancelled"];

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
  const canMatch = hasPermission(user, "match.run") && !!mission && !TERMINAL_STATUSES.includes(mission.status);

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
        <p className="text-sm text-muted-foreground">
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
                <span className="text-sm">
                  {req.skill_name} ≥{req.min_proficiency} · {req.filled_count}/{req.required_count}
                </span>
                <div className="h-2 w-full rounded-full bg-muted" role="progressbar" aria-valuenow={pct}>
                  <div className="h-2 rounded-full bg-primary" style={{ width: `${pct}%` }} />
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
          <h3 className="text-sm font-medium">Roster</h3>
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
          <ul className="flex flex-col gap-2" aria-label="Roster">
            {staffing.roster.map((entry) => (
              <li key={entry.assignment_id} className="flex flex-wrap items-center gap-2 text-sm">
                <span className="font-medium">{entry.name}</span>
                <Badge variant={entry.status === "accepted" ? "default" : "secondary"}>{entry.status}</Badge>
                {/* Soft conflict: overlapping but non-blocking commitment elsewhere — a
                    warning, surfaced via popover, never disables anything. */}
                {entry.soft_conflicts.length > 0 && (
                  <Popover>
                    <PopoverTrigger className="cursor-pointer">
                      <Badge variant="outline" className="border-amber-500 text-amber-600">
                        Conflict
                      </Badge>
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
                {entry.hard_blocked && <Badge variant="destructive">Unavailable</Badge>}
                {canManage && (
                  <Button
                    size="sm"
                    variant="outline"
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
