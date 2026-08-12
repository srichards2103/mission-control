import { useState } from "react";
import { Link } from "react-router-dom";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { MISSION_STATUSES, useMissions } from "@/features/missions/api/missions";
import { MissionCreateDialog } from "@/features/missions/components/mission-create-dialog";
import { MISSION_STATUS_LABELS, MissionStatusBadge } from "@/features/missions/components/mission-status-badge";
import { hasPermission, useUser } from "@/lib/auth";

const ALL = "all";

export function MissionsPage() {
  const [status, setStatus] = useState<string>(ALL);
  const { data: user } = useUser();
  const { data: missions, isLoading, isError } = useMissions(status === ALL ? undefined : status);

  let body: React.ReactNode;
  if (isLoading) {
    body = <p className="text-sm text-muted-foreground">Loading missions…</p>;
  } else if (isError) {
    body = (
      <p role="alert" className="text-sm text-destructive">
        Couldn&apos;t load missions. Please try again.
      </p>
    );
  } else {
    body = (
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Dates</TableHead>
            <TableHead>Crew</TableHead>
            <TableHead>Lead</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {missions?.map((mission) => (
            <TableRow key={mission.id}>
              <TableCell>
                <Link to={`/missions/${mission.id}`} className="font-medium hover:underline">
                  {mission.name}
                </Link>
              </TableCell>
              <TableCell>
                <MissionStatusBadge status={mission.status} />
              </TableCell>
              <TableCell>
                {mission.start_date} – {mission.end_date}
              </TableCell>
              <TableCell>
                {mission.min_crew}–{mission.max_crew}
              </TableCell>
              <TableCell>{mission.created_by.name}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Missions</h1>
        {hasPermission(user, "mission.create") && <MissionCreateDialog />}
      </div>
      <Tabs value={status} onValueChange={(value) => setStatus(value as string)}>
        <TabsList>
          <TabsTrigger value={ALL}>All</TabsTrigger>
          {MISSION_STATUSES.map((s) => (
            <TabsTrigger key={s} value={s}>
              {MISSION_STATUS_LABELS[s]}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>
      {body}
    </div>
  );
}
