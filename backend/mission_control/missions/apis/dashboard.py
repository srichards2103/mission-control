"""Dashboard API: expose Task 6.1's org dashboard selectors over HTTP.

Read-only. One view, four selector calls -- `pipeline_summary`, `staffing_readiness`,
`crew_utilization`, `skill_gaps` -- each called exactly once (staffing_readiness's
1 + 3N query cost is a known, ruled-acceptable limitation; calling it twice per
request would double it for nothing). No number is recomputed here: every field below
is a straight pass-through of what the selector already returned, serialized
explicitly (by name) rather than dumped generically, so this is the one place the
wire contract for the dashboard is written down.
"""

from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from mission_control.missions.selectors.dashboard import (
    crew_utilization,
    pipeline_summary,
    skill_gaps,
    staffing_readiness,
)
from mission_control.users.permissions import Permission, ensure_permission


class StatusCountsSerializer(serializers.Serializer):
    """The seven mission statuses, enumerated by name (not a generic DictField) so an
    eighth status added to the FSM later is a visible serializer change, not a
    silently-passed-through key."""

    draft = serializers.IntegerField()
    pending_approval = serializers.IntegerField()
    approved = serializers.IntegerField()
    rejected = serializers.IntegerField()
    active = serializers.IntegerField()
    completed = serializers.IntegerField()
    cancelled = serializers.IntegerField()


class PendingApprovalSerializer(serializers.Serializer):
    mission_id = serializers.IntegerField()
    name = serializers.CharField()
    submitted_at = serializers.DateTimeField()
    age_days = serializers.IntegerField()


class UpcomingMissionSerializer(serializers.Serializer):
    mission_id = serializers.IntegerField()
    name = serializers.CharField()
    start_date = serializers.DateField()
    days_until = serializers.IntegerField()


class PipelineSerializer(serializers.Serializer):
    status_counts = StatusCountsSerializer()
    pending_approvals = PendingApprovalSerializer(many=True)
    upcoming = UpcomingMissionSerializer(many=True)


class ReadinessRowSerializer(serializers.Serializer):
    mission_id = serializers.IntegerField()
    name = serializers.CharField()
    status = serializers.CharField()
    start_date = serializers.DateField()
    coverage_pct = serializers.IntegerField()
    accepted_count = serializers.IntegerField()
    min_crew = serializers.IntegerField()
    fully_covered = serializers.BooleanField()
    at_risk = serializers.BooleanField()


class CrewUtilizationRowSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    name = serializers.CharField()
    assigned_days = serializers.IntegerField()
    utilization_pct = serializers.IntegerField()


class UtilizationSerializer(serializers.Serializer):
    window_days = serializers.IntegerField()
    org_utilization_pct = serializers.IntegerField()
    crew = CrewUtilizationRowSerializer(many=True)


class SkillGapSerializer(serializers.Serializer):
    skill_id = serializers.IntegerField()
    skill_name = serializers.CharField()
    # One row per (skill, threshold): a skill required at two proficiencies produces two
    # rows, because the crew who clear the easier one do not clear the harder one.
    min_proficiency = serializers.IntegerField()
    open_seats = serializers.IntegerField()
    qualified_crew = serializers.IntegerField()
    gap = serializers.BooleanField()


class DashboardApi(APIView):
    def get(self, request):
        ensure_permission(request.user, Permission.DASHBOARD_VIEW)
        return Response(
            {
                "pipeline": PipelineSerializer(pipeline_summary()).data,
                "readiness": ReadinessRowSerializer(staffing_readiness(), many=True).data,
                "utilization": UtilizationSerializer(crew_utilization()).data,
                "skill_gaps": SkillGapSerializer(skill_gaps(), many=True).data,
            }
        )
