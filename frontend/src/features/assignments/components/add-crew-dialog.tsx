import { useEffect, useState } from "react";
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
import { Label } from "@/components/ui/label";
import { useProposeAssignments } from "@/features/assignments/api/assignments";
import { useCrew } from "@/features/crew/api/crew";
import { errorMessage } from "@/lib/api-errors";

type AddCrewDialogProps = {
  missionId: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  currentRosterUserIds: number[];
};

export function AddCrewDialog({
  missionId,
  open,
  onOpenChange,
  currentRosterUserIds,
}: AddCrewDialogProps) {
  const { data: crew, isLoading, isError } = useCrew();
  const proposeAssignments = useProposeAssignments(missionId);
  const [selected, setSelected] = useState<number[]>([]);
  const [formError, setFormError] = useState<string | null>(null);

  // Reset selection/errors each time the dialog opens, so a previous session's picks
  // or error message don't linger into the next.
  useEffect(() => {
    if (open) {
      setSelected([]);
      setFormError(null);
    }
  }, [open]);

  const rosterIds = new Set(currentRosterUserIds);
  const candidates = (crew ?? []).filter((member) => !rosterIds.has(member.id));

  function toggle(userId: number) {
    setSelected((prev) =>
      prev.includes(userId) ? prev.filter((id) => id !== userId) : [...prev, userId],
    );
  }

  async function handlePropose() {
    setFormError(null);
    try {
      await proposeAssignments.mutateAsync(selected);
      toast.success("Crew proposed");
      onOpenChange(false);
    } catch (err) {
      setFormError(errorMessage(err));
      toast.error(errorMessage(err));
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add crew</DialogTitle>
          <DialogDescription>Propose crew members for this mission.</DialogDescription>
        </DialogHeader>
        <div className="flex max-h-64 flex-col gap-2 overflow-y-auto">
          {isLoading && <p className="text-sm text-muted-foreground">Loading crew…</p>}
          {isError && (
            <p role="alert" className="text-sm text-destructive">
              Couldn&apos;t load crew. Please try again.
            </p>
          )}
          {!isLoading && !isError && candidates.length === 0 && (
            <p className="text-sm text-muted-foreground">No crew available to add.</p>
          )}
          {candidates.map((member) => (
            <div key={member.id} className="flex items-center gap-2">
              <input
                type="checkbox"
                id={`add-crew-${member.id}`}
                checked={selected.includes(member.id)}
                onChange={() => toggle(member.id)}
              />
              <Label htmlFor={`add-crew-${member.id}`}>{member.name}</Label>
            </div>
          ))}
        </div>
        {formError && (
          <p role="alert" className="text-sm text-destructive">
            {formError}
          </p>
        )}
        <DialogFooter>
          <Button onClick={handlePropose} disabled={selected.length === 0 || proposeAssignments.isPending}>
            {proposeAssignments.isPending ? "Proposing…" : "Propose"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
