import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
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
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useProposeAssignments } from "@/features/assignments/api/assignments";
import { useRunMatch } from "@/features/matching/api/matching";
import { errorMessage } from "@/lib/api-errors";
import { hasPermission, useUser } from "@/lib/auth";
import { cn } from "@/lib/utils";

type MatchDialogProps = {
  missionId: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

// Who currently fills a given seat, once a swap has replaced the matcher's original
// pick. Keyed by `${requirement_id}:${slot owner's user_id}`, where "slot owner" is
// always the *original* matcher-proposed team member for that seat (stable across
// repeated swaps) -- NOT by requirement_id alone: a requirement with
// required_count > 1 can be covered by two different team members, each with their
// own seats[] entry carrying the same requirement_id, so requirement_id alone can't
// tell those two seats apart. Absent entries mean "still whoever the matcher
// proposed."
type Swap = { user_id: number; name: string };

function swapKey(requirementId: number, slotOwnerUserId: number) {
  return `${requirementId}:${slotOwnerUserId}`;
}

export function MatchDialog({ missionId, open, onOpenChange }: MatchDialogProps) {
  const { data: user } = useUser();
  const runMatch = useRunMatch(missionId);
  const proposeAssignments = useProposeAssignments(missionId);
  // Opening the dialog is gated on match.run alone (see staffing-panel.tsx), so a
  // user with match.run but not assignment.manage can still run the matcher and see
  // why -- they just can't act on it. Same split staffing-panel.tsx already makes
  // between viewing the roster and Add crew/Remove.
  const canPropose = hasPermission(user, "assignment.manage");
  // The bulk-propose selection: user_ids that will be posted. Starts as every
  // team member the matcher proposed (default checked, per the brief) and is
  // adjusted by unchecking a member's own checkbox or swapping a seat for an
  // alternative (which unchecks the original holder and checks the alternative).
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [swaps, setSwaps] = useState<Record<string, Swap>>({});
  const [formError, setFormError] = useState<string | null>(null);

  function runAndSeed() {
    setFormError(null);
    setSwaps({});
    runMatch.mutate(undefined, {
      onSuccess: (result) => setSelected(new Set(result.team.map((m) => m.user_id))),
    });
  }

  // Re-run automatically every time the dialog opens, per the brief's "on open -> run
  // match" flow -- a lead should never see a stale team from a previous open.
  useEffect(() => {
    if (open) runAndSeed();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const result = runMatch.data;

  function toggleMember(userId: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(userId)) next.delete(userId);
      else next.add(userId);
      return next;
    });
  }

  // `slotOwnerUserId` is the original matcher-proposed team member for this seat --
  // stable across repeated swaps, used only as the `swaps` map key.
  // `currentHolderUserId` is whoever the seat is filled by *right now* (the slot
  // owner if unswapped, or the previously swapped-in candidate) -- this is who must
  // be removed from `selected` so a second swap on the same seat replaces the first
  // candidate rather than leaving them behind as a phantom extra proposal.
  function handleSwap(
    requirementId: number,
    slotOwnerUserId: number,
    currentHolderUserId: number,
    candidateUserId: string | null,
  ) {
    if (!result || !candidateUserId) return;
    const candidate = result.alternatives
      .find((alt) => alt.requirement_id === requirementId)
      ?.candidates.find((c) => String(c.user_id) === candidateUserId);
    if (!candidate) return;
    setSelected((prev) => {
      const next = new Set(prev);
      next.delete(currentHolderUserId);
      next.add(candidate.user_id);
      return next;
    });
    setSwaps((prev) => ({
      ...prev,
      [swapKey(requirementId, slotOwnerUserId)]: { user_id: candidate.user_id, name: candidate.name },
    }));
  }

  async function handlePropose() {
    setFormError(null);
    try {
      const userIds = Array.from(selected);
      await proposeAssignments.mutateAsync(userIds);
      toast.success(`Proposed ${userIds.length} assignments`);
      onOpenChange(false);
    } catch (err) {
      setFormError(errorMessage(err));
      toast.error(errorMessage(err));
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Auto-match</DialogTitle>
          <DialogDescription>
            Proposed crew for this mission&apos;s open seats. Adjust the selection, then propose.
          </DialogDescription>
        </DialogHeader>

        {/* isLoading -> isError -> data, in that order, per the panel-wide convention
            (see staffing-panel.tsx et al.) -- runMatch is a mutation rather than a
            query, but the same branch order applies. */}
        {runMatch.isPending && <p className="text-sm text-muted-foreground">Matching…</p>}
        {runMatch.isError && (
          <p role="alert" className="text-sm text-destructive">
            {errorMessage(runMatch.error)}
          </p>
        )}

        {result && (
          <div className="flex flex-col gap-4">
            {result.team.length === 0 ? (
              <p className="text-sm text-muted-foreground">No crew proposed.</p>
            ) : (
              <ul className="flex flex-col gap-3">
                {result.team.map((member) => {
                  const isSelected = selected.has(member.user_id);
                  return (
                  <li
                    key={member.user_id}
                    className={cn(
                      "flex flex-col gap-2 rounded-lg border p-3 transition-opacity",
                      // Finding 2 fix: an unchecked member (whether unchecked directly or
                      // as the fallout of a swap on one of their seats) must be visibly
                      // distinct, not just reflected in the checkbox's `checked` prop --
                      // a generalist covering two seats who loses one to a swap still has
                      // their *other* seat's badge rendered, and without this the lead
                      // has no way to see that seat is no longer actually proposed.
                      !isSelected && "border-dashed opacity-60",
                    )}
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <input
                        type="checkbox"
                        id={`match-member-${member.user_id}`}
                        checked={isSelected}
                        onChange={() => toggleMember(member.user_id)}
                      />
                      <Label htmlFor={`match-member-${member.user_id}`} className="font-medium">
                        {member.name}
                      </Label>
                      {!isSelected && (
                        <span className="text-xs italic text-muted-foreground">(not proposed)</span>
                      )}
                      <Popover>
                        <PopoverTrigger className="cursor-pointer text-sm text-muted-foreground underline decoration-dotted underline-offset-2">
                          Score {member.score.toFixed(2)}
                        </PopoverTrigger>
                        <PopoverContent>
                          <ul className="flex flex-col gap-1 text-xs">
                            <li>Fit: {member.breakdown.proficiency_fit}</li>
                            <li>Workload: {member.breakdown.workload_balance}</li>
                            <li>Conflict penalty: {member.breakdown.soft_conflict_penalty}</li>
                          </ul>
                        </PopoverContent>
                      </Popover>
                      {/* Soft conflict: a warning, never a reason to disable this
                          member -- same rule as the staffing panel's roster chip. */}
                      {member.soft_conflicts.length > 0 && (
                        <Popover>
                          <PopoverTrigger className="cursor-pointer">
                            <Badge variant="outline" className="border-amber-500 text-amber-600">
                              Conflict
                            </Badge>
                          </PopoverTrigger>
                          <PopoverContent>
                            <ul className="flex flex-col gap-1 text-xs">
                              {member.soft_conflicts.map((conflict, index) => (
                                <li key={index}>
                                  {conflict.mission_name} ({conflict.mission_status}, {conflict.assignment_status})
                                </li>
                              ))}
                            </ul>
                          </PopoverContent>
                        </Popover>
                      )}
                    </div>
                    <div className="flex flex-col gap-2">
                      {member.seats.map((seat) => {
                        const swap = swaps[swapKey(seat.requirement_id, member.user_id)];
                        // Who to actually remove from `selected` on the *next* swap of
                        // this seat: the previously swapped-in candidate if there is
                        // one, otherwise the original slot owner. See handleSwap's
                        // comment -- this is Finding 1's fix.
                        const currentHolderUserId = swap ? swap.user_id : member.user_id;
                        const alt = result.alternatives.find((a) => a.requirement_id === seat.requirement_id);
                        return (
                          <div key={seat.requirement_id} className="flex flex-wrap items-center gap-2">
                            <Badge variant="secondary">
                              {seat.skill_name} ≥{seat.min_proficiency}
                            </Badge>
                            {swap && <Badge variant="outline">Swapped in: {swap.name}</Badge>}
                            {alt && alt.candidates.length > 0 && (
                              <Select value={swap ? String(swap.user_id) : ""} onValueChange={(value) =>
                                handleSwap(seat.requirement_id, member.user_id, currentHolderUserId, value)
                              }>
                                <SelectTrigger
                                  size="sm"
                                  aria-label={`Swap ${seat.skill_name} ≥${seat.min_proficiency}`}
                                >
                                  <SelectValue placeholder="Swap for alternative…" />
                                </SelectTrigger>
                                <SelectContent>
                                  {alt.candidates.map((candidate) => (
                                    <SelectItem key={candidate.user_id} value={String(candidate.user_id)}>
                                      {candidate.name} (score {candidate.score})
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </li>
                  );
                })}
              </ul>
            )}

            {result.unfilled_seats.length > 0 && (
              <div className="flex flex-col gap-1">
                <h3 className="text-sm font-medium text-destructive">Unfilled seats</h3>
                <ul className="flex flex-col gap-1">
                  {result.unfilled_seats.map((seat, index) => (
                    <li key={index} className="text-sm text-destructive">
                      {seat.skill_name} ≥{seat.min_proficiency} — {seat.reason}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {formError && (
          <p role="alert" className="text-sm text-destructive">
            {formError}
          </p>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={runAndSeed} disabled={runMatch.isPending}>
            Re-run
          </Button>
          {canPropose && (
            <Button
              onClick={handlePropose}
              disabled={!result || selected.size === 0 || proposeAssignments.isPending}
            >
              {proposeAssignments.isPending ? "Proposing…" : `Propose ${selected.size} assignments`}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
