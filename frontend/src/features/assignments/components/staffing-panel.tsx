import { useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { useRemoveAssignment, useStaffing } from "@/features/assignments/api/assignments";
import { AddCrewDialog } from "@/features/assignments/components/add-crew-dialog";
import { errorMessage } from "@/lib/api-errors";
import { hasPermission, useUser } from "@/lib/auth";

export function StaffingPanel({ missionId }: { missionId: number }) {
  const { data: user } = useUser();
  const { data: staffing, isLoading, isError } = useStaffing(missionId);
  const removeAssignment = useRemoveAssignment(missionId);
  const [addCrewOpen, setAddCrewOpen] = useState(false);
  const canManage = hasPermission(user, "assignment.manage");

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
    try {
      await removeAssignment.mutateAsync(assignmentId);
    } catch (err) {
      toast.error(errorMessage(err));
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
          {canManage && (
            <Button size="sm" onClick={() => setAddCrewOpen(true)}>
              Add crew
            </Button>
          )}
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
                    disabled={removeAssignment.isPending}
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
    </div>
  );
}
