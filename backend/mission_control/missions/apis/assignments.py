from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from mission_control.common.pagination import get_paginated_response
from mission_control.missions.models import Assignment, Mission
from mission_control.missions.selectors import missions as mission_selectors
from mission_control.missions.selectors.staffing import (
    hard_blocked_user_ids,
    mission_coverage,
    soft_conflicts_for_users,
)
from mission_control.missions.services import assignments as services
from mission_control.users.permissions import Permission, ensure_permission


def staffing_payload(mission: Mission) -> dict:
    """The shared staffing response shape, reused by the staffing GET and every write
    that mutates it (bulk propose, remove) -- so a client always sees the same, fresh
    picture of the mission's crew after any of those calls.

    Composes three of Task 4.2's selectors: `mission_coverage` for requirement fill,
    `mission_assignments` for the live roster, and `soft_conflicts_for_users` /
    `hard_blocked_user_ids` (with `exclude_mission_id=mission.id`, since this range
    belongs to the mission being staffed) for each roster member's availability. No
    date/status predicate is written here -- everything staffing-related is read
    straight from `missions.selectors.staffing`.
    """
    coverage = mission_coverage(mission)
    roster_assignments = list(mission_selectors.mission_assignments(mission))
    user_ids = [a.user_id for a in roster_assignments]

    soft_conflicts = soft_conflicts_for_users(
        user_ids=user_ids,
        start_date=mission.start_date,
        end_date=mission.end_date,
        exclude_mission_id=mission.id,
    )
    blocked = hard_blocked_user_ids(
        start_date=mission.start_date, end_date=mission.end_date, exclude_mission_id=mission.id
    )

    return {
        "requirements": [
            {
                "requirement_id": r.requirement_id,
                "skill_id": r.skill_id,
                "skill_name": r.skill_name,
                "min_proficiency": r.min_proficiency,
                "required_count": r.required_count,
                "filled_count": r.filled_count,
                "filled_by": r.filled_by,
            }
            for r in coverage.requirements
        ],
        "accepted_count": coverage.accepted_count,
        "min_crew": mission.min_crew,
        "max_crew": mission.max_crew,
        "fully_covered": coverage.fully_covered,
        "roster": [
            {
                "assignment_id": a.id,
                "user_id": a.user_id,
                "name": a.user.name,
                "status": a.status,
                # soft_conflicts_for_users omits users with no conflicts -- .get(..., []).
                "soft_conflicts": soft_conflicts.get(a.user_id, []),
                "hard_blocked": a.user_id in blocked,
            }
            for a in roster_assignments
        ],
    }


class AssignmentOutputSerializer(serializers.Serializer):
    """The "my-assignments shape": used both by the list and by respond's single-row reply."""

    id = serializers.IntegerField()
    status = serializers.CharField()
    decline_reason = serializers.CharField()
    responded_at = serializers.DateTimeField(allow_null=True)
    mission = serializers.SerializerMethodField()

    def get_mission(self, assignment):
        mission = assignment.mission
        return {
            "id": mission.id,
            "name": mission.name,
            "status": mission.status,
            "start_date": mission.start_date,
            "end_date": mission.end_date,
            "description": mission.description,
        }


class MissionStaffingApi(APIView):
    def get(self, request, mission_id: int):
        ensure_permission(request.user, Permission.MISSION_VIEW)
        mission = mission_selectors.mission_get(mission_id)
        return Response(staffing_payload(mission))


class MissionAssignmentsBulkApi(APIView):
    class InputSerializer(serializers.Serializer):
        user_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)

    def post(self, request, mission_id: int):
        ensure_permission(request.user, Permission.ASSIGNMENT_MANAGE)
        mission = mission_selectors.mission_get(mission_id)
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.assignments_propose(
            actor=request.user, mission=mission, user_ids=serializer.validated_data["user_ids"]
        )
        mission = mission_selectors.mission_get(mission_id)
        return Response(staffing_payload(mission), status=status.HTTP_201_CREATED)


class AssignmentRemoveApi(APIView):
    def post(self, request, assignment_id: int):
        ensure_permission(request.user, Permission.ASSIGNMENT_MANAGE)
        # Scoped manager (`Assignment.objects`) -- another tenant's assignment is a
        # 404, never a 403.
        assignment = get_object_or_404(
            Assignment.objects.select_related("mission", "user"), id=assignment_id
        )
        services.assignment_remove(actor=request.user, assignment=assignment)
        mission = mission_selectors.mission_get(assignment.mission_id)
        return Response(staffing_payload(mission))


class MyAssignmentsApi(APIView):
    def get(self, request):
        ensure_permission(request.user, Permission.ASSIGNMENT_RESPOND)
        queryset = mission_selectors.my_assignments(request.user)
        return get_paginated_response(
            serializer_class=AssignmentOutputSerializer, queryset=queryset, request=request
        )


class AssignmentRespondApi(APIView):
    class InputSerializer(serializers.Serializer):
        action = serializers.ChoiceField(choices=["accept", "decline"])
        reason = serializers.CharField(required=False, allow_blank=True, default="")

    def post(self, request, assignment_id: int):
        ensure_permission(request.user, Permission.ASSIGNMENT_RESPOND)
        assignment = get_object_or_404(
            Assignment.objects.select_related("mission", "user"), id=assignment_id
        )
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assignment = services.assignment_respond(
            actor=request.user, assignment=assignment, **serializer.validated_data
        )
        return Response(AssignmentOutputSerializer(assignment).data)
