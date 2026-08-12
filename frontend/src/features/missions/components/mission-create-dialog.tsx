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
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useCreateMission } from "@/features/missions/api/missions";
import { errorMessage, fieldErrorsFrom } from "@/lib/api-errors";

export function MissionCreateDialog() {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [minCrew, setMinCrew] = useState("1");
  const [maxCrew, setMaxCrew] = useState("1");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string[]>>({});
  const createMission = useCreateMission();

  function reset() {
    setName("");
    setDescription("");
    setStartDate("");
    setEndDate("");
    setMinCrew("1");
    setMaxCrew("1");
    setFieldErrors({});
  }

  // Mirrors the backend's two CHECK constraints (mission_dates_ordered,
  // mission_crew_bounds) so the obviously-invalid case is caught before the round
  // trip. The server's full_clean() still enforces these authoritatively — this is
  // just a fast client-side echo of the same rule, not a replacement for it.
  function clientValidationErrors(): string[] {
    const errors: string[] = [];
    if (startDate && endDate && endDate < startDate) {
      errors.push("End date must be on or after the start date.");
    }
    const min = Number(minCrew);
    const max = Number(maxCrew);
    if (Number.isFinite(min) && Number.isFinite(max) && max < min) {
      errors.push("Max crew must be at least min crew.");
    }
    return errors;
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setFieldErrors({});
    const clientErrors = clientValidationErrors();
    if (clientErrors.length > 0) {
      setFieldErrors({ non_field_errors: clientErrors });
      return;
    }
    try {
      await createMission.mutateAsync({
        name,
        description,
        start_date: startDate,
        end_date: endDate,
        min_crew: Number(minCrew),
        max_crew: Number(maxCrew),
      });
      reset();
      setOpen(false);
    } catch (err) {
      setFieldErrors(fieldErrorsFrom(err));
      toast.error(errorMessage(err));
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) reset();
      }}
    >
      <DialogTrigger render={<Button />}>New mission</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New mission</DialogTitle>
          <DialogDescription>Create a draft mission to start planning.</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="mission-name">Name</Label>
            <Input id="mission-name" value={name} onChange={(e) => setName(e.target.value)} required />
            {fieldErrors.name && (
              <p role="alert" className="text-sm text-destructive">
                {fieldErrors.name.join(" ")}
              </p>
            )}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="mission-description">Description</Label>
            <Input
              id="mission-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
            {fieldErrors.description && (
              <p role="alert" className="text-sm text-destructive">{fieldErrors.description.join(" ")}</p>
            )}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="mission-start-date">Start date</Label>
              <Input
                id="mission-start-date"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                required
              />
              {fieldErrors.start_date && (
                <p role="alert" className="text-sm text-destructive">{fieldErrors.start_date.join(" ")}</p>
              )}
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="mission-end-date">End date</Label>
              <Input
                id="mission-end-date"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                required
              />
              {fieldErrors.end_date && (
                <p role="alert" className="text-sm text-destructive">{fieldErrors.end_date.join(" ")}</p>
              )}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="mission-min-crew">Min crew</Label>
              <Input
                id="mission-min-crew"
                type="number"
                min={1}
                value={minCrew}
                onChange={(e) => setMinCrew(e.target.value)}
                required
              />
              {fieldErrors.min_crew && (
                <p role="alert" className="text-sm text-destructive">{fieldErrors.min_crew.join(" ")}</p>
              )}
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="mission-max-crew">Max crew</Label>
              <Input
                id="mission-max-crew"
                type="number"
                min={1}
                value={maxCrew}
                onChange={(e) => setMaxCrew(e.target.value)}
                required
              />
              {fieldErrors.max_crew && (
                <p role="alert" className="text-sm text-destructive">{fieldErrors.max_crew.join(" ")}</p>
              )}
            </div>
          </div>
          {fieldErrors.non_field_errors && (
            <p role="alert" className="text-sm text-destructive">
              {fieldErrors.non_field_errors.join(" ")}
            </p>
          )}
          <DialogFooter>
            <Button type="submit" disabled={createMission.isPending}>
              {createMission.isPending ? "Creating…" : "Create mission"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
