import { MISSION_STATUS_LABELS } from "@/features/missions/components/mission-status-badge";
import type { MissionDetail } from "@/features/missions/api/missions";

export function MissionHistory({ history }: { history: MissionDetail["history"] }) {
  if (history.length === 0) {
    return <p className="text-sm text-muted-foreground">No history yet.</p>;
  }

  // Reverse-chronological per the brief; the server appends in chronological order.
  const entries = [...history].reverse();

  return (
    <ul className="flex flex-col gap-3">
      {entries.map((entry, index) => (
        <li key={`${entry.created_at}-${index}`} className="text-sm">
          <p>
            <span className="font-medium">{entry.actor_name}</span> moved{" "}
            {MISSION_STATUS_LABELS[entry.from_status]} → {MISSION_STATUS_LABELS[entry.to_status]}
          </p>
          {entry.reason && <p className="text-muted-foreground">{entry.reason}</p>}
          <p className="text-xs text-muted-foreground">{new Date(entry.created_at).toLocaleString()}</p>
        </li>
      ))}
    </ul>
  );
}
