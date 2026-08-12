import { Link, useParams } from "react-router-dom";
import { useMission } from "@/features/missions/api/missions";
import { MissionHistory } from "@/features/missions/components/mission-history";
import { MissionStatusBadge } from "@/features/missions/components/mission-status-badge";
import { RequirementsEditor } from "@/features/missions/components/requirements-editor";
import { TransitionButtons } from "@/features/missions/components/transition-buttons";

export function MissionDetailPage() {
  const { missionId } = useParams<{ missionId: string }>();
  const id = Number(missionId);
  const { data: mission, isLoading, isError } = useMission(id);

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading mission…</p>;
  }
  // isLoading -> isError -> data, in that order (see missions-page.tsx / crew-detail-page.tsx):
  // an unparseable :missionId must also render the alert, not hang on a query that
  // never runs (useMission disables itself via `enabled: Number.isFinite(id)`).
  if (!Number.isFinite(id) || isError || !mission) {
    return (
      <p role="alert" className="text-sm text-destructive">
        Couldn&apos;t load this mission. Please try again.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <Link to="/missions" className="text-sm text-muted-foreground hover:underline">
        ← Back to missions
      </Link>

      <div className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-xl font-semibold">{mission.name}</h1>
          <MissionStatusBadge status={mission.status} />
        </div>
        <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-muted-foreground">
          <span>
            {mission.start_date} – {mission.end_date}
          </span>
          <span>
            Crew {mission.min_crew}–{mission.max_crew}
          </span>
          <span>Lead: {mission.created_by.name}</span>
        </div>
        {mission.description && <p className="text-sm">{mission.description}</p>}
        <TransitionButtons mission={mission} />
      </div>

      <section className="flex flex-col gap-2">
        <h2 className="text-lg font-medium">Requirements</h2>
        <RequirementsEditor mission={mission} />
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="text-lg font-medium">Staffing</h2>
        <p className="text-sm text-muted-foreground">Staffing tools arrive in Stage 4.</p>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="text-lg font-medium">History</h2>
        <MissionHistory history={mission.history} />
      </section>
    </div>
  );
}
