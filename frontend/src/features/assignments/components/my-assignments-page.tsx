import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { PageHeader, SectionLabel } from "@/components/ui/page-header";
import { StatusDot, type StatusDotColor } from "@/components/ui/status-dot";
import { useMyAssignments, useRespondAssignment, type MyAssignment } from "@/features/assignments/api/assignments";
import { TERMINAL_MISSION_STATUSES } from "@/features/missions/components/mission-status-badge";
import { errorMessage } from "@/lib/api-errors";

const ASSIGNMENT_STATUS_LABELS: Record<MyAssignment["status"], string> = {
  proposed: "Proposed",
  accepted: "Accepted",
  declined: "Declined",
  removed: "Removed",
};

const ASSIGNMENT_STATUS_DOTS: Record<MyAssignment["status"], { color: StatusDotColor; muted?: boolean }> = {
  proposed: { color: "amber" },
  accepted: { color: "green" },
  declined: { color: "red" },
  removed: { color: "gray", muted: true },
};

function isUpcoming(assignment: MyAssignment): boolean {
  return assignment.status === "accepted" && !TERMINAL_MISSION_STATUSES.includes(assignment.mission.status);
}

function AssignmentRow({
  assignment,
  right,
  muted = false,
}: {
  assignment: MyAssignment;
  right?: React.ReactNode;
  muted?: boolean;
}) {
  return (
    <li className="flex items-start justify-between gap-4 border-b py-2.5 last:border-0">
      <div className="flex min-w-0 flex-col gap-0.5">
        <span className={muted ? "text-sm font-medium text-muted-foreground" : "text-sm font-medium"}>
          {assignment.mission.name}
        </span>
        <span className="num text-xs text-muted-foreground">
          {assignment.mission.start_date} – {assignment.mission.end_date}
        </span>
        {assignment.mission.description && (
          <span className="text-sm text-muted-foreground">{assignment.mission.description}</span>
        )}
        {assignment.status === "declined" && assignment.decline_reason && (
          <span className="text-sm text-muted-foreground">Reason: {assignment.decline_reason}</span>
        )}
      </div>
      {right && <div className="flex shrink-0 items-center gap-2 pt-0.5">{right}</div>}
    </li>
  );
}

export function MyAssignmentsPage() {
  const { data: assignments, isLoading, isError } = useMyAssignments();
  const respondAssignment = useRespondAssignment();
  // Tracks which single assignment is mid-response, so an in-flight accept/decline
  // only disables that row's own buttons rather than every row's (respondAssignment
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
    <div className="flex flex-col gap-6">
      <PageHeader title="My assignments" />

      <section className="flex flex-col gap-2">
        <SectionLabel>Pending proposals</SectionLabel>
        {pending.length === 0 ? (
          <p className="text-sm text-muted-foreground">No pending proposals.</p>
        ) : (
          <ul className="flex flex-col border-y">
            {pending.map((assignment) => (
              <AssignmentRow
                key={assignment.id}
                assignment={assignment}
                right={
                  <>
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
                  </>
                }
              />
            ))}
          </ul>
        )}
      </section>

      <section className="flex flex-col gap-2">
        <SectionLabel>Upcoming</SectionLabel>
        {upcoming.length === 0 ? (
          <p className="text-sm text-muted-foreground">No upcoming assignments.</p>
        ) : (
          <ul className="flex flex-col border-y">
            {upcoming.map((assignment) => (
              <AssignmentRow key={assignment.id} assignment={assignment} />
            ))}
          </ul>
        )}
      </section>

      <section className="flex flex-col gap-2">
        <SectionLabel>History</SectionLabel>
        {history.length === 0 ? (
          <p className="text-sm text-muted-foreground">No history yet.</p>
        ) : (
          <ul className="flex flex-col border-y">
            {history.map((assignment) => (
              <AssignmentRow
                key={assignment.id}
                assignment={assignment}
                muted
                right={
                  <StatusDot
                    color={ASSIGNMENT_STATUS_DOTS[assignment.status].color}
                    muted={ASSIGNMENT_STATUS_DOTS[assignment.status].muted}
                  >
                    {ASSIGNMENT_STATUS_LABELS[assignment.status]}
                  </StatusDot>
                }
              />
            ))}
          </ul>
        )}
      </section>

      <Dialog open={decliningId !== null} onOpenChange={(open) => !open && setDecliningId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Decline proposal</DialogTitle>
            <DialogDescription>A reason is optional.</DialogDescription>
          </DialogHeader>
          <Field label="Reason (optional)" htmlFor="decline-reason">
            <Input
              id="decline-reason"
              value={declineReason}
              onChange={(e) => setDeclineReason(e.target.value)}
            />
          </Field>
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
