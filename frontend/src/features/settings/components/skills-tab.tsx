import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { FieldError } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { StatusDot } from "@/components/ui/status-dot";
import { RowActions, Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
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
            <TableCell className={skill.is_archived ? "text-muted-foreground" : "font-medium"}>
              {skill.name}
            </TableCell>
            <TableCell className="text-muted-foreground">{skill.description}</TableCell>
            <TableCell>
              {skill.is_archived ? (
                <StatusDot color="gray" muted>Archived</StatusDot>
              ) : (
                <StatusDot color="green">Active</StatusDot>
              )}
            </TableCell>
            <RowActions>
              <Button size="sm" variant="ghost" onClick={() => toggleArchived(skill.id, skill.is_archived)}>
                {skill.is_archived ? "Restore" : "Archive"}
              </Button>
            </RowActions>
          </TableRow>
        ))}
        <TableRow className="hover:bg-transparent">
          <TableCell className="py-2 align-top">
            <Input placeholder="New skill name" value={name} onChange={(e) => setName(e.target.value)} />
            {fieldErrors.name && <FieldError>{fieldErrors.name.join(" ")}</FieldError>}
            {fieldErrors.non_field_errors && (
              <FieldError>{fieldErrors.non_field_errors.join(" ")}</FieldError>
            )}
          </TableCell>
          <TableCell className="py-2 align-top">
            <Input
              placeholder="Description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
            {fieldErrors.description && <FieldError>{fieldErrors.description.join(" ")}</FieldError>}
          </TableCell>
          <TableCell />
          <TableCell className="py-2 text-right align-top">
            <Button size="sm" onClick={handleAdd} disabled={createSkill.isPending}>
              Add skill
            </Button>
          </TableCell>
        </TableRow>
      </TableBody>
    </Table>
  );
}
