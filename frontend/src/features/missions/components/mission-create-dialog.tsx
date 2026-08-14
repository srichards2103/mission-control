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
import { Field, FieldError } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
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
          <Field label="Name" htmlFor="mission-name" errors={fieldErrors.name}>
            <Input id="mission-name" value={name} onChange={(e) => setName(e.target.value)} required />
          </Field>
          <Field label="Description" htmlFor="mission-description" errors={fieldErrors.description}>
            <Input
              id="mission-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Start date" htmlFor="mission-start-date" errors={fieldErrors.start_date}>
              <Input
                id="mission-start-date"
                type="date"
                className="num"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                required
              />
            </Field>
            <Field label="End date" htmlFor="mission-end-date" errors={fieldErrors.end_date}>
              <Input
                id="mission-end-date"
                type="date"
                className="num"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                required
              />
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Min crew" htmlFor="mission-min-crew" errors={fieldErrors.min_crew}>
              <Input
                id="mission-min-crew"
                type="number"
                min={1}
                className="num"
                value={minCrew}
                onChange={(e) => setMinCrew(e.target.value)}
                required
              />
            </Field>
            <Field label="Max crew" htmlFor="mission-max-crew" errors={fieldErrors.max_crew}>
              <Input
                id="mission-max-crew"
                type="number"
                min={1}
                className="num"
                value={maxCrew}
                onChange={(e) => setMaxCrew(e.target.value)}
                required
              />
            </Field>
          </div>
          {fieldErrors.non_field_errors && (
            <FieldError>{fieldErrors.non_field_errors.join(" ")}</FieldError>
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
