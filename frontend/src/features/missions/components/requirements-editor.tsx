import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useSetRequirements, type MissionDetail } from "@/features/missions/api/missions";
import { useSkills } from "@/features/skills/api/skills";
import { errorMessage, rowErrorsFrom } from "@/lib/api-errors";

const PROFICIENCIES = Array.from({ length: 10 }, (_, i) => i + 1);
// Default proficiency/count for a newly added row: the minimum valid values, so a
// freshly-added row never silently claims a higher-than-intended requirement before
// the editor picks one. Not specified by the brief.
const DEFAULT_MIN_PROFICIENCY = 1;
const DEFAULT_REQUIRED_COUNT = 1;

type Row = { skill_id: number; skill_name: string; min_proficiency: number; required_count: number };

function toRows(requirements: MissionDetail["requirements"]): Row[] {
  return requirements.map(({ skill_id, skill_name, min_proficiency, required_count }) => ({
    skill_id,
    skill_name,
    min_proficiency,
    required_count,
  }));
}

export function RequirementsEditor({ mission }: { mission: MissionDetail }) {
  const editable = mission.status === "draft" || mission.status === "rejected";
  const { data: allSkills, isLoading: skillsLoading, isError: skillsError } = useSkills();
  const setRequirements = useSetRequirements(mission.id);

  const [draft, setDraft] = useState<Row[]>(() => toRows(mission.requirements));
  const [pendingSkillId, setPendingSkillId] = useState("");
  const [rowErrors, setRowErrors] = useState<Record<number, string[]>>({});
  const [formError, setFormError] = useState<string | null>(null);

  // Re-sync whenever we land on a different mission, or the mission re-enters an
  // editable state (e.g. after "Revise" moves rejected -> draft) — not on every
  // requirements change, so an in-flight edit isn't clobbered by an unrelated
  // background refetch.
  useEffect(() => {
    setDraft(toRows(mission.requirements));
    setRowErrors({});
    setFormError(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mission.id, mission.status]);

  if (!editable) {
    if (mission.requirements.length === 0) {
      return <p className="text-sm text-muted-foreground">No requirements set.</p>;
    }
    return (
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Skill</TableHead>
            <TableHead>Min proficiency</TableHead>
            <TableHead>Count</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {mission.requirements.map((req) => (
            <TableRow key={req.id}>
              <TableCell>{req.skill_name}</TableCell>
              <TableCell>≥ {req.min_proficiency}</TableCell>
              <TableCell>× {req.required_count}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    );
  }

  const chosenIds = new Set(draft.map((row) => row.skill_id));
  const availableSkills = (allSkills ?? []).filter((skill) => !skill.is_archived && !chosenIds.has(skill.id));

  function updateRow(skillId: number, patch: Partial<Pick<Row, "min_proficiency" | "required_count">>) {
    setDraft((prev) => prev.map((row) => (row.skill_id === skillId ? { ...row, ...patch } : row)));
  }

  function removeRow(skillId: number) {
    setDraft((prev) => prev.filter((row) => row.skill_id !== skillId));
  }

  function addRow(skillIdValue: string | null) {
    const skill = availableSkills.find((s) => String(s.id) === skillIdValue);
    if (!skill) return;
    setDraft((prev) => [
      ...prev,
      {
        skill_id: skill.id,
        skill_name: skill.name,
        min_proficiency: DEFAULT_MIN_PROFICIENCY,
        required_count: DEFAULT_REQUIRED_COUNT,
      },
    ]);
    setPendingSkillId("");
  }

  async function handleSave() {
    setRowErrors({});
    setFormError(null);
    try {
      await setRequirements.mutateAsync(
        draft.map(({ skill_id, min_proficiency, required_count }) => ({
          skill_id,
          min_proficiency,
          required_count,
        })),
      );
      toast.success("Requirements saved");
    } catch (err) {
      const perRow = rowErrorsFrom(err);
      setRowErrors(perRow);
      // Even a payload we can't map to a specific row (a 500, a network error, an
      // envelope shape rowErrorsFrom() doesn't recognise) must still show the user
      // something rather than failing silently.
      setFormError(errorMessage(err));
      toast.error(errorMessage(err));
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Skill</TableHead>
            <TableHead>Min proficiency</TableHead>
            <TableHead>Count</TableHead>
            <TableHead />
          </TableRow>
        </TableHeader>
        <TableBody>
          {draft.map((row, index) => (
            <TableRow key={row.skill_id}>
              <TableCell>
                {row.skill_name}
                {rowErrors[index] && (
                  <p role="alert" className="text-xs text-destructive">
                    {rowErrors[index].join(" ")}
                  </p>
                )}
              </TableCell>
              <TableCell>
                <Select
                  value={String(row.min_proficiency)}
                  onValueChange={(value) => updateRow(row.skill_id, { min_proficiency: Number(value) })}
                >
                  <SelectTrigger size="sm" aria-label={`Min proficiency for ${row.skill_name}`}>
                    <SelectValue>{(value: string) => value}</SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    {PROFICIENCIES.map((p) => (
                      <SelectItem key={p} value={String(p)}>
                        {p}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </TableCell>
              <TableCell>
                <Input
                  type="number"
                  min={1}
                  aria-label={`Count for ${row.skill_name}`}
                  className="w-20"
                  value={row.required_count}
                  onChange={(e) => updateRow(row.skill_id, { required_count: Number(e.target.value) })}
                />
              </TableCell>
              <TableCell>
                <Button
                  size="sm"
                  variant="outline"
                  aria-label={`Remove ${row.skill_name}`}
                  onClick={() => removeRow(row.skill_id)}
                >
                  Remove
                </Button>
              </TableCell>
            </TableRow>
          ))}
          <TableRow>
            <TableCell colSpan={4}>
              {skillsError ? (
                <p role="alert" className="text-sm text-destructive">
                  Couldn&apos;t load skills to add.
                </p>
              ) : (
                <Select value={pendingSkillId} onValueChange={addRow} disabled={skillsLoading}>
                  <SelectTrigger size="sm" aria-label="Add a skill requirement">
                    <SelectValue placeholder={skillsLoading ? "Loading skills…" : "Add a skill"}>
                      {(value: string) => availableSkills.find((s) => String(s.id) === value)?.name ?? value}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    {availableSkills.map((skill) => (
                      <SelectItem key={skill.id} value={String(skill.id)}>
                        {skill.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
      {formError && (
        <p role="alert" className="text-sm text-destructive">
          {formError}
        </p>
      )}
      <div>
        <Button onClick={handleSave} disabled={setRequirements.isPending}>
          {setRequirements.isPending ? "Saving…" : "Save requirements"}
        </Button>
      </div>
    </div>
  );
}
