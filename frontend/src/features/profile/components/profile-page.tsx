import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { PageHeader } from "@/components/ui/page-header";
import { RowActions, Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useMySkills, useSetMySkills, type MySkill } from "@/features/profile/api/profile";
import { useSkills } from "@/features/skills/api/skills";
import { errorMessage, rowErrorsFrom } from "@/lib/api-errors";

const PROFICIENCIES = Array.from({ length: 10 }, (_, i) => i + 1);
// Default proficiency for a newly added row: 1 (the minimum valid value), so a
// freshly-added skill never silently claims a higher-than-intended proficiency
// before the crew member has picked one. Not specified by the brief.
const DEFAULT_PROFICIENCY = 1;

export function ProfilePage() {
  const { data: mySkills, isLoading, isError } = useMySkills();
  const { data: allSkills, isLoading: skillsLoading, isError: skillsError } = useSkills();
  const setMySkills = useSetMySkills();

  // Local draft, replace-the-whole-collection semantics: initialised once from the
  // fetched profile, then mutated freely (add/remove/change proficiency) until Save.
  // Re-synced from the server's response after a successful save (not from a
  // background refetch) so the draft always reflects exactly what the server has,
  // without clobbering in-flight edits if the invalidated query refetches later.
  const [draft, setDraft] = useState<MySkill[] | null>(null);
  const [pendingSkillId, setPendingSkillId] = useState<string>("");
  // Row-index-keyed validation errors from the last failed save (e.g. proficiency
  // out of range on one specific row) -- see rowErrorsFrom() in lib/api-errors.ts.
  const [rowErrors, setRowErrors] = useState<Record<number, string[]>>({});

  useEffect(() => {
    if (mySkills && draft === null) setDraft(mySkills);
  }, [mySkills, draft]);

  // isLoading -> isError -> data, in that order: if we let a "draft still empty"
  // check run ahead of isError, a failed fetch renders "Loading profile…" forever
  // instead of the alert (draft never gets populated once the query errors).
  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading profile…</p>;
  }
  if (isError) {
    return (
      <p role="alert" className="text-sm text-destructive">
        Couldn&apos;t load your profile. Please try again.
      </p>
    );
  }
  if (draft === null) {
    return <p className="text-sm text-muted-foreground">Loading profile…</p>;
  }

  const chosenIds = new Set(draft.map((row) => row.skill_id));
  const availableSkills = (allSkills ?? []).filter((skill) => !skill.is_archived && !chosenIds.has(skill.id));

  function updateProficiency(skillId: number, proficiency: number) {
    setDraft((prev) => prev!.map((row) => (row.skill_id === skillId ? { ...row, proficiency } : row)));
  }

  function removeSkill(skillId: number) {
    setDraft((prev) => prev!.filter((row) => row.skill_id !== skillId));
  }

  function addSkill(skillIdValue: string | null) {
    const skill = availableSkills.find((s) => String(s.id) === skillIdValue);
    if (!skill) return;
    setDraft((prev) => [...prev!, { skill_id: skill.id, skill_name: skill.name, proficiency: DEFAULT_PROFICIENCY }]);
    setPendingSkillId("");
  }

  async function handleSave() {
    setRowErrors({});
    try {
      // Send exactly the draft — including an empty array when every row has been
      // removed, which the server treats as "wipe the profile" (a real, supported
      // outcome, not an accidental no-op).
      const saved = await setMySkills.mutateAsync(
        draft!.map(({ skill_id, proficiency }) => ({ skill_id, proficiency })),
      );
      setDraft(saved);
      toast.success("Profile saved");
    } catch (err) {
      // Draft is left exactly as the user had it — a failed save must be recoverable,
      // not silently reset or discarded. PUT /api/v1/me/skills/ takes a bulk `items`
      // array, so a per-row validation error (e.g. proficiency out of range on one
      // skill) comes back index-keyed rather than under a flat field name -- surface
      // it against the right row rather than just a generic toast.
      setRowErrors(rowErrorsFrom(err));
      toast.error(errorMessage(err));
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="My Profile" />
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Skill</TableHead>
            <TableHead>Proficiency</TableHead>
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
                  value={String(row.proficiency)}
                  onValueChange={(value) => updateProficiency(row.skill_id, Number(value))}
                >
                  <SelectTrigger size="sm" aria-label={`Proficiency for ${row.skill_name}`}>
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
              <RowActions>
                <Button
                  size="sm"
                  variant="ghost"
                  aria-label={`Remove ${row.skill_name}`}
                  onClick={() => removeSkill(row.skill_id)}
                >
                  Remove
                </Button>
              </RowActions>
            </TableRow>
          ))}
          <TableRow>
            <TableCell colSpan={3}>
              {skillsError ? (
                <p role="alert" className="text-sm text-destructive">
                  Couldn&apos;t load skills to add.
                </p>
              ) : (
                <Select value={pendingSkillId} onValueChange={addSkill} disabled={skillsLoading}>
                  <SelectTrigger size="sm" className="min-w-40" aria-label="Add a skill">
                    <SelectValue placeholder={skillsLoading ? "Loading skills…" : "Add a skill"}>
                      {(value: string) =>
                        value
                          ? (availableSkills.find((s) => String(s.id) === value)?.name ?? value)
                          : (skillsLoading ? "Loading skills…" : "Add a skill")
                      }
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
      <div>
        <Button onClick={handleSave} disabled={setMySkills.isPending}>
          {setMySkills.isPending ? "Saving…" : "Save"}
        </Button>
      </div>
    </div>
  );
}
