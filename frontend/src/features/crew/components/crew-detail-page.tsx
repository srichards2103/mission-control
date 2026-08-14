import { Link, useParams } from "react-router-dom";
import { SectionLabel } from "@/components/ui/page-header";
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
    <div className="flex flex-col gap-6">
      <Link to="/crew" className="text-xs text-muted-foreground hover:text-foreground">
        ← Back to crew
      </Link>
      <div className="flex flex-col gap-1">
        <h1 className="text-[15px] leading-none font-semibold tracking-[-0.01em]">{member.name}</h1>
        <p className="text-xs text-muted-foreground">{member.email}</p>
      </div>
      <section className="flex max-w-md flex-col gap-2">
        <SectionLabel>Skills</SectionLabel>
        {member.skills.length === 0 ? (
          <p className="text-sm text-muted-foreground">No skills recorded.</p>
        ) : (
          <ul className="flex flex-col border-y">
            {member.skills.map((skill) => (
              <li
                key={skill.skill_id}
                className="flex h-8 items-center justify-between border-b text-sm last:border-0"
              >
                <span>{skill.name}</span>
                <span className="num text-muted-foreground">{skill.proficiency}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
