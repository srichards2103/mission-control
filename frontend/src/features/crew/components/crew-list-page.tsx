import { Link } from "react-router-dom";
import { PageHeader } from "@/components/ui/page-header";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useCrew } from "@/features/crew/api/crew";
import { sortByName } from "@/lib/utils";

export function CrewListPage() {
  const { data: crew, isLoading, isError } = useCrew();

  if (isLoading) return <p className="text-sm text-muted-foreground">Loading crew…</p>;
  if (isError) {
    return (
      <p role="alert" className="text-sm text-destructive">
        Couldn&apos;t load the crew directory. Please try again.
      </p>
    );
  }

  const sorted = sortByName(crew ?? [], (member) => member.name);

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="Crew" />
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Email</TableHead>
            <TableHead>Skills</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sorted.map((member) => (
            <TableRow key={member.id}>
              <TableCell>
                <Link to={`/crew/${member.id}`} className="font-medium hover:underline">
                  {member.name}
                </Link>
              </TableCell>
              <TableCell className="text-muted-foreground">{member.email}</TableCell>
              <TableCell className="num text-muted-foreground">
                {member.skills.map((skill) => `${skill.name} ${skill.proficiency}`).join(" · ")}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
