import { useState } from "react";
import { AxiosError } from "axios";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useCreateSkill, useSkills, useUpdateSkill } from "@/features/skills/api/skills";

function errorMessage(err: unknown): string {
  if (err instanceof AxiosError && typeof err.response?.data?.message === "string") {
    return err.response.data.message;
  }
  return "Something went wrong. Please try again.";
}

export function SkillsTab() {
  const { data: skills, isLoading } = useSkills();
  const createSkill = useCreateSkill();
  const updateSkill = useUpdateSkill();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  async function handleAdd() {
    if (!name.trim()) return;
    try {
      await createSkill.mutateAsync({ name, description });
      setName("");
      setDescription("");
    } catch (err) {
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
          </TableCell>
          <TableCell>
            <Input
              placeholder="Description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
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
