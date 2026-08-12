import { useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useMyAssignments, useRespondAssignment, type MyAssignment } from "@/features/assignments/api/assignments";
import { errorMessage } from "@/lib/api-errors";

const ASSIGNMENT_STATUS_LABELS: Record<MyAssignment["status"], string> = {
  proposed: "Proposed",
  accepted: "Accepted",
  declined: "Declined",
  removed: "Removed",
};

// Mission statuses past which an accepted assignment is no longer "upcoming" work --
// mirrors MISSION_STATUSES in features/missions/api/missions.ts.
const TERMINAL_MISSION_STATUSES = new Set(["completed", "cancelled"]);

function isUpcoming(assignment: MyAssignment): boolean {
  return assignment.status === "accepted" && !TERMINAL_MISSION_STATUSES.has(assignment.mission.status);
}

function MissionDates({ assignment }: { assignment: MyAssignment }) {
  return (
    <p className="text-sm text-muted-foreground">
      {assignment.mission.start_date} – {assignment.mission.end_date}
    </p>
  );
}

export function MyAssignmentsPage() {
  const { data: assignments, isLoading, isError } = useMyAssignments();
  const respondAssignment = useRespondAssignment();
  // Tracks which single assignment is mid-response, so an in-flight accept/decline
  // only disables that card's own buttons rather than every card's (respondAssignment
  // is one shared mutation object for the whole page).
  const [respondingId, setRespondingId] = useState<number | null>(null);
  const [decliningId, setDecliningId] = useState<number | null>(null);
  const [declineReason, setDeclineReason] = useState("");

  // isLoading -> isError -> data, in that order (see staffing-panel.tsx / mission-detail-page.tsx):
  // data?.map must never run before both checks.
  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading assignments…</p>;
  }
  if (isError || !assignments) {
    return (
      <p role="alert" className="text-sm text-destructive">
        Couldn&apos;t load your assignments. Please try again.
      </p>
    );
  }

  const pending = assignments.filter((a) => a.status === "proposed");
  const upcoming = assignments.filter(isUpcoming);
  const history = assignments.filter((a) => a.status !== "proposed" && !isUpcoming(a));

  async function handleAccept(assignmentId: number) {
    setRespondingId(assignmentId);
    try {
      await respondAssignment.mutateAsync({ assignmentId, action: "accept" });
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setRespondingId(null);
    }
  }

  function openDecline(assignmentId: number) {
    setDecliningId(assignmentId);
    setDeclineReason("");
  }

  async function handleDecline() {
    if (decliningId === null) return;
    setRespondingId(decliningId);
    try {
      await respondAssignment.mutateAsync({
        assignmentId: decliningId,
        action: "decline",
        reason: declineReason.trim() || undefined,
      });
      setDecliningId(null);
      setDeclineReason("");
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setRespondingId(null);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <h1 className="text-xl font-semibold">My assignments</h1>

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-medium">Pending proposals</h2>
        {pending.length === 0 ? (
          <p className="text-sm text-muted-foreground">No pending proposals.</p>
        ) : (
          <div className="flex flex-col gap-3">
            {pending.map((assignment) => (
              <Card key={assignment.id}>
                <CardHeader>
                  <CardTitle>{assignment.mission.name}</CardTitle>
                </CardHeader>
                <CardContent className="flex flex-col gap-2">
                  <MissionDates assignment={assignment} />
                  {assignment.mission.description && (
                    <p className="text-sm">{assignment.mission.description}</p>
                  )}
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      disabled={respondingId === assignment.id}
                      onClick={() => handleAccept(assignment.id)}
                    >
                      Accept
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={respondingId === assignment.id}
                      onClick={() => openDecline(assignment.id)}
                    >
                      Decline
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-medium">Upcoming</h2>
        {upcoming.length === 0 ? (
          <p className="text-sm text-muted-foreground">No upcoming assignments.</p>
        ) : (
          <div className="flex flex-col gap-3">
            {upcoming.map((assignment) => (
              <Card key={assignment.id}>
                <CardHeader>
                  <CardTitle>{assignment.mission.name}</CardTitle>
                </CardHeader>
                <CardContent className="flex flex-col gap-2">
                  <MissionDates assignment={assignment} />
                  {assignment.mission.description && (
                    <p className="text-sm">{assignment.mission.description}</p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-medium">History</h2>
        {history.length === 0 ? (
          <p className="text-sm text-muted-foreground">No history yet.</p>
        ) : (
          <div className="flex flex-col gap-3">
            {history.map((assignment) => (
              <Card key={assignment.id} className="text-muted-foreground opacity-75">
                <CardHeader>
                  <div className="flex flex-wrap items-center gap-2">
                    <CardTitle className="text-muted-foreground">{assignment.mission.name}</CardTitle>
                    <Badge variant="secondary">{ASSIGNMENT_STATUS_LABELS[assignment.status]}</Badge>
                  </div>
                </CardHeader>
                <CardContent className="flex flex-col gap-1">
                  <MissionDates assignment={assignment} />
                  {assignment.status === "declined" && assignment.decline_reason && (
                    <p className="text-sm">Reason: {assignment.decline_reason}</p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </section>

      <Dialog open={decliningId !== null} onOpenChange={(open) => !open && setDecliningId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Decline proposal</DialogTitle>
            <DialogDescription>A reason is optional.</DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="decline-reason">Reason (optional)</Label>
            <Input
              id="decline-reason"
              value={declineReason}
              onChange={(e) => setDeclineReason(e.target.value)}
            />
          </div>
          <DialogFooter>
            <Button
              variant="destructive"
              disabled={decliningId !== null && respondingId === decliningId}
              onClick={handleDecline}
            >
              Decline
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
