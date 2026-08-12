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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useTransitionMission, type MissionDetail, type MissionStatus } from "@/features/missions/api/missions";
import { TERMINAL_MISSION_STATUSES } from "@/features/missions/components/mission-status-badge";
import { errorMessage } from "@/lib/api-errors";
import { hasPermission, useUser } from "@/lib/auth";

type TransitionAction = "submit" | "approve" | "reject" | "revise" | "activate" | "complete";

type ActionDef = { action: TransitionAction; label: string; permission: string; requiresReason?: boolean };

// Which actions are offered from each status, and the permission that gates each one.
// This is only "which buttons to show" — the actual guards (≥1 requirement, dates,
// no self-approval, etc.) are enforced server-side and are not re-implemented here.
const ACTIONS_BY_STATUS: Record<MissionStatus, ActionDef[]> = {
  draft: [{ action: "submit", label: "Submit", permission: "mission.progress" }],
  pending_approval: [
    { action: "approve", label: "Approve", permission: "mission.review" },
    { action: "reject", label: "Reject", permission: "mission.review", requiresReason: true },
  ],
  approved: [{ action: "activate", label: "Activate", permission: "mission.progress" }],
  rejected: [{ action: "revise", label: "Revise", permission: "mission.progress" }],
  active: [{ action: "complete", label: "Complete", permission: "mission.progress" }],
  completed: [],
  cancelled: [],
};

type ReasonDialogState = { action: "reject" | "cancel"; reason: string } | null;

export function TransitionButtons({ mission }: { mission: MissionDetail }) {
  const { data: user } = useUser();
  const transitionMission = useTransitionMission(mission.id);
  const [dialog, setDialog] = useState<ReasonDialogState>(null);

  async function runTransition(action: string, reason?: string) {
    try {
      await transitionMission.mutateAsync(reason ? { action, reason } : { action });
      setDialog(null);
    } catch (err) {
      toast.error(errorMessage(err));
    }
  }

  // Approve/Reject are hidden for the mission's creator — no self-approval, per the
  // brief. (The backend also excludes the submitter, which isn't on the detail
  // shape, so it can't be checked client-side; the server enforces that half.)
  const isCreator = user?.id === mission.created_by.id;
  const actions = ACTIONS_BY_STATUS[mission.status].filter((def) => {
    if (!hasPermission(user, def.permission)) return false;
    if ((def.action === "approve" || def.action === "reject") && isCreator) return false;
    return true;
  });
  const canCancel =
    !TERMINAL_MISSION_STATUSES.includes(mission.status) && hasPermission(user, "mission.progress");

  if (actions.length === 0 && !canCancel) return null;

  return (
    <div className="flex flex-wrap gap-2">
      {actions.map((def) =>
        def.requiresReason ? (
          <Button
            key={def.action}
            variant="destructive"
            onClick={() => setDialog({ action: def.action as "reject", reason: "" })}
          >
            {def.label}
          </Button>
        ) : (
          <Button key={def.action} onClick={() => runTransition(def.action)} disabled={transitionMission.isPending}>
            {def.label}
          </Button>
        ),
      )}
      {canCancel && (
        <Button variant="destructive" onClick={() => setDialog({ action: "cancel", reason: "" })}>
          Cancel
        </Button>
      )}

      <Dialog open={dialog !== null} onOpenChange={(open) => !open && setDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{dialog?.action === "reject" ? "Reject mission" : "Cancel mission"}</DialogTitle>
            <DialogDescription>A reason is required.</DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="transition-reason">Reason</Label>
            <Input
              id="transition-reason"
              value={dialog?.reason ?? ""}
              onChange={(e) => setDialog((prev) => (prev ? { ...prev, reason: e.target.value } : prev))}
              required
            />
          </div>
          <DialogFooter>
            <Button
              variant="destructive"
              disabled={!dialog?.reason.trim() || transitionMission.isPending}
              onClick={() => dialog && runTransition(dialog.action, dialog.reason)}
            >
              {dialog?.action === "reject" ? "Reject" : "Cancel mission"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
