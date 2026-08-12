import { useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useCreateSkill, useSkills, useUpdateSkill } from "@/features/skills/api/skills";
import { errorMessage, fieldErrorsFrom } from "@/lib/api-errors";

export function SkillsTab() {
  const { data: skills, isLoading, isError } = useSkills();
  const createSkill = useCreateSkill();
  const updateSkill = useUpdateSkill();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string[]>>({});

  async function handleAdd() {
    if (!name.trim()) return;
    setFieldErrors({});
    try {
      await createSkill.mutateAsync({ name, description });
      setName("");
      setDescription("");
    } catch (err) {
      setFieldErrors(fieldErrorsFrom(err));
      toast.error(errorMessage(err));
    }
  }

  function toggleArchived(skillId: number, isArchived: boolean) {
    updateSkill.mutate(
      { id: skillId, is_archived: !isArchived },
      { onError: (err) => toast.error(errorMessage(err)) },
    );
  }

  if (isLoading) return <p className="text-sm text-muted-foreground">Loading skills…</p>;
  if (isError) {
    return (
      <p role="alert" className="text-sm text-destructive">
        Couldn&apos;t load skills. Please try again.
      </p>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead>Description</TableHead>
          <TableHead>Status</TableHead>
          <TableHead />
        </TableRow>
      </TableHeader>
      <TableBody>
        {skills?.map((skill) => (
          <TableRow key={skill.id}>
            <TableCell>{skill.name}</TableCell>
            <TableCell>{skill.description}</TableCell>
            <TableCell>{skill.is_archived && <Badge variant="outline">Archived</Badge>}</TableCell>
            <TableCell>
              <Button size="sm" variant="outline" onClick={() => toggleArchived(skill.id, skill.is_archived)}>
                {skill.is_archived ? "Restore" : "Archive"}
              </Button>
            </TableCell>
          </TableRow>
        ))}
        <TableRow>
          <TableCell>
            <Input placeholder="New skill name" value={name} onChange={(e) => setName(e.target.value)} />
            {fieldErrors.name && <p className="text-sm text-destructive">{fieldErrors.name.join(" ")}</p>}
            {fieldErrors.non_field_errors && (
              <p role="alert" className="text-sm text-destructive">
                {fieldErrors.non_field_errors.join(" ")}
              </p>
            )}
          </TableCell>
          <TableCell>
            <Input
              placeholder="Description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
            {fieldErrors.description && (
              <p className="text-sm text-destructive">{fieldErrors.description.join(" ")}</p>
            )}
          </TableCell>
          <TableCell />
          <TableCell>
            <Button size="sm" onClick={handleAdd} disabled={createSkill.isPending}>
              Add skill
            </Button>
          </TableCell>
        </TableRow>
      </TableBody>
    </Table>
  );
}
