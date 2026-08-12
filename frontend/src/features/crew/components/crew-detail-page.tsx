import { Link, useParams } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { useCrewMember } from "@/features/crew/api/crew";

export function CrewDetailPage() {
  const { crewId } = useParams<{ crewId: string }>();
  const userId = Number(crewId);
  const { data: member, isLoading, isError } = useCrewMember(userId);

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading crew member…</p>;
  }
  if (!Number.isFinite(userId) || isError || !member) {
    return (
      <p role="alert" className="text-sm text-destructive">
        Couldn&apos;t load this crew member. Please try again.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <Link to="/crew" className="text-sm text-muted-foreground hover:underline">
        ← Back to crew
      </Link>
      <Card className="max-w-md">
        <CardHeader>
          {/* CardTitle renders a <div>, not a semantic heading, so an explicit <h1>
              is used here to give the page an accessible heading role. */}
          <h1 className="font-heading text-base leading-snug font-medium">{member.name}</h1>
          <p className="text-sm text-muted-foreground">{member.email}</p>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-1">
          {member.skills.length === 0 ? (
            <p className="text-sm text-muted-foreground">No skills recorded.</p>
          ) : (
            member.skills.map((skill) => (
              <Badge key={skill.skill_id} variant="secondary">
                {skill.name} {skill.proficiency}
              </Badge>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
