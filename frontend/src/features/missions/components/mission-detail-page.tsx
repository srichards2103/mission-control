import { Link, useParams } from "react-router-dom";
import { SectionLabel } from "@/components/ui/page-header";
import { StaffingPanel } from "@/features/assignments/components/staffing-panel";
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
      <Link to="/missions" className="text-xs text-muted-foreground hover:text-foreground">
        ← Back to missions
      </Link>

      <div className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-[15px] leading-none font-semibold tracking-[-0.01em]">{mission.name}</h1>
          <MissionStatusBadge status={mission.status} />
        </div>
        <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted-foreground">
          <span className="num">
            {mission.start_date} – {mission.end_date}
          </span>
          <span className="num">
            Crew {mission.min_crew}–{mission.max_crew}
          </span>
          <span>Lead: {mission.created_by.name}</span>
        </div>
        {mission.description && <p className="text-sm">{mission.description}</p>}
        <TransitionButtons mission={mission} />
      </div>

      <section className="flex flex-col gap-2">
        <SectionLabel>Requirements</SectionLabel>
        <RequirementsEditor mission={mission} />
      </section>

      <section className="flex flex-col gap-2">
        <SectionLabel>Staffing</SectionLabel>
        <StaffingPanel missionId={mission.id} />
      </section>

      <section className="flex flex-col gap-2">
        <SectionLabel>History</SectionLabel>
        <MissionHistory history={mission.history} />
      </section>
    </div>
  );
}
