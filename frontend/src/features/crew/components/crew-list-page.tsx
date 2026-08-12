import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useCrew } from "@/features/crew/api/crew";

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

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">Crew</h1>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Email</TableHead>
            <TableHead>Skills</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {crew?.map((member) => (
            <TableRow key={member.id}>
              <TableCell>
                <Link to={`/crew/${member.id}`} className="font-medium hover:underline">
                  {member.name}
                </Link>
              </TableCell>
              <TableCell>{member.email}</TableCell>
              <TableCell>
                <div className="flex flex-wrap gap-1">
                  {member.skills.map((skill) => (
                    <Badge key={skill.skill_id} variant="secondary">
                      {skill.name} {skill.proficiency}
                    </Badge>
                  ))}
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
