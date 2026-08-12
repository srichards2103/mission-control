import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { useDashboard, type CrewUtilizationRow, type ReadinessRow } from "@/features/dashboard/api/dashboard";
import { MISSION_STATUS_LABELS } from "@/features/missions/components/mission-status-badge";
import { MISSION_STATUSES } from "@/features/missions/api/missions";

function CoverageBar({ pct }: { pct: number }) {
  const clamped = Math.min(100, Math.max(0, pct));
  return (
    <div
      role="progressbar"
      aria-valuenow={clamped}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label="Seats filled"
      className="h-2 w-full overflow-hidden rounded-full bg-muted"
    >
      <div
        className={cn("h-full rounded-full", clamped >= 100 ? "bg-primary" : "bg-amber-500")}
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
}

function ReadinessRowView({ row }: { row: ReadinessRow }) {
  return (
    <li
      className={cn(
        "flex flex-col gap-1.5 rounded-lg border p-3",
        row.at_risk && "border-destructive/50 bg-destructive/5",
      )}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Link to={`/missions/${row.mission_id}`} className="font-medium hover:underline">
          {row.name}
        </Link>
        {row.at_risk && <Badge variant="destructive">At risk</Badge>}
      </div>
      <CoverageBar pct={row.coverage_pct} />
      <p className="text-xs text-muted-foreground">
        {row.coverage_pct}% of seats filled &middot; {row.accepted_count}/{row.min_crew} min crew accepted
        &middot; starts {row.start_date}
      </p>
    </li>
  );
}

function CrewUtilizationRowView({ row, windowDays }: { row: CrewUtilizationRow; windowDays: number }) {
  return (
    <li className="flex items-center justify-between gap-2 text-sm">
      <span>{row.name}</span>
      <span className="text-muted-foreground">
        {row.utilization_pct}% &middot; {row.assigned_days}/{windowDays} days
      </span>
    </li>
  );
}

export function DashboardPage() {
  const { data, isLoading, isError } = useDashboard();

  if (isLoading) {
    return (
      <p role="status" aria-live="polite" className="text-sm text-muted-foreground">
        Loading dashboard…
      </p>
    );
  }
  if (isError || !data) {
    return (
      <p role="alert" className="text-sm text-destructive">
        Couldn&apos;t load the dashboard. Please try again.
      </p>
    );
  }

  const { pipeline, readiness, utilization, skill_gaps: skillGaps } = data;
  const atRiskFirst = readiness; // staffing_readiness() already returns at-risk-first
  const busiest = utilization.crew.slice(0, 5);
  const leastBusy = [...utilization.crew].slice(-5).reverse();
  const gapsFirst = skillGaps; // skill_gaps() already returns gap-rows-first

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">Dashboard</h1>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Pipeline */}
        <Card>
          <CardHeader>
            <CardTitle>Pipeline</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="flex flex-wrap gap-1.5">
              {MISSION_STATUSES.map((status) => (
                <Badge key={status} variant="secondary">
                  {MISSION_STATUS_LABELS[status]}: {pipeline.status_counts[status]}
                </Badge>
              ))}
            </div>

            <div>
              <h3 className="mb-1.5 text-sm font-medium">Pending approval</h3>
              {pipeline.pending_approvals.length === 0 ? (
                <p className="text-sm text-muted-foreground">Nothing is awaiting approval.</p>
              ) : (
                <ul className="flex flex-col gap-1.5">
                  {pipeline.pending_approvals.map((m) => (
                    <li key={m.mission_id} className="flex items-center justify-between gap-2 text-sm">
                      <Link to={`/missions/${m.mission_id}`} className="hover:underline">
                        {m.name}
                      </Link>
                      <Badge variant="outline">
                        {m.age_days === 0 ? "Submitted today" : `${m.age_days}d waiting`}
                      </Badge>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div>
              <h3 className="mb-1.5 text-sm font-medium">Starting soon</h3>
              {pipeline.upcoming.length === 0 ? (
                <p className="text-sm text-muted-foreground">Nothing starts in the next 30 days.</p>
              ) : (
                <ul className="flex flex-col gap-1.5">
                  {pipeline.upcoming.map((m) => (
                    <li key={m.mission_id} className="flex items-center justify-between gap-2 text-sm">
                      <Link to={`/missions/${m.mission_id}`} className="hover:underline">
                        {m.name}
                      </Link>
                      <span className="text-muted-foreground">
                        {m.days_until === 0 ? "today" : `in ${m.days_until}d`}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Staffing readiness */}
        <Card>
          <CardHeader>
            <CardTitle>Staffing readiness</CardTitle>
          </CardHeader>
          <CardContent>
            {atRiskFirst.length === 0 ? (
              <p className="text-sm text-muted-foreground">No live missions need staffing right now.</p>
            ) : (
              <ul className="flex flex-col gap-2">
                {atRiskFirst.map((row) => (
                  <ReadinessRowView key={row.mission_id} row={row} />
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        {/* Crew utilization */}
        <Card>
          <CardHeader>
            <CardTitle>Crew utilization</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <p className="text-2xl font-semibold">
              {utilization.org_utilization_pct}%
              <span className="ml-2 text-sm font-normal text-muted-foreground">
                org-wide utilization over the next {utilization.window_days} days
              </span>
            </p>
            {utilization.crew.length === 0 ? (
              <p className="text-sm text-muted-foreground">No active crew members.</p>
            ) : (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <h3 className="mb-1.5 text-sm font-medium">Busiest</h3>
                  <ul className="flex flex-col gap-1">
                    {busiest.map((row) => (
                      <CrewUtilizationRowView key={row.user_id} row={row} windowDays={utilization.window_days} />
                    ))}
                  </ul>
                </div>
                <div>
                  <h3 className="mb-1.5 text-sm font-medium">Least busy</h3>
                  <ul className="flex flex-col gap-1">
                    {leastBusy.map((row) => (
                      <CrewUtilizationRowView key={row.user_id} row={row} windowDays={utilization.window_days} />
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Skill gaps */}
        <Card>
          <CardHeader>
            <CardTitle>Skill gaps</CardTitle>
          </CardHeader>
          <CardContent>
            {gapsFirst.length === 0 ? (
              <p className="text-sm text-muted-foreground">No open missions currently need skills.</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Skill</TableHead>
                    <TableHead>Open seats</TableHead>
                    <TableHead>Qualified crew</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {gapsFirst.map((row) => (
                    <TableRow
                      key={`${row.skill_id}:${row.min_proficiency}`}
                      className={cn(row.gap && "bg-destructive/5")}
                    >
                      <TableCell>
                        {row.skill_name} &ge;{row.min_proficiency}
                      </TableCell>
                      <TableCell>{row.open_seats}</TableCell>
                      <TableCell>{row.qualified_crew}</TableCell>
                      <TableCell>
                        {row.gap ? (
                          <Badge variant="destructive">Gap</Badge>
                        ) : (
                          <Badge variant="secondary">Covered</Badge>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
