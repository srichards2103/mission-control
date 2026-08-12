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

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setFieldErrors({});
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
            {fieldErrors.name && <p className="text-sm text-destructive">{fieldErrors.name.join(" ")}</p>}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="mission-description">Description</Label>
            <Input
              id="mission-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
            {fieldErrors.description && (
              <p className="text-sm text-destructive">{fieldErrors.description.join(" ")}</p>
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
                <p className="text-sm text-destructive">{fieldErrors.start_date.join(" ")}</p>
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
                <p className="text-sm text-destructive">{fieldErrors.end_date.join(" ")}</p>
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
                <p className="text-sm text-destructive">{fieldErrors.min_crew.join(" ")}</p>
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
                <p className="text-sm text-destructive">{fieldErrors.max_crew.join(" ")}</p>
              )}
            </div>
          </div>
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
