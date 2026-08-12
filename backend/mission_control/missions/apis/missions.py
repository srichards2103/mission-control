from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from mission_control.common.pagination import get_paginated_response
from mission_control.missions.selectors import missions as selectors
from mission_control.missions.services import missions as services
from mission_control.users.permissions import Permission, ensure_permission


class MissionListItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    status = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    min_crew = serializers.IntegerField()
    max_crew = serializers.IntegerField()
    created_by = serializers.SerializerMethodField()

    def get_created_by(self, m):
        return {"id": m.created_by_id, "name": m.created_by.name}


class MissionDetailSerializer(MissionListItemSerializer):
    description = serializers.CharField()
    requirements = serializers.SerializerMethodField()
    history = serializers.SerializerMethodField()

    def get_requirements(self, m):
        return [
            {
                "id": r.id,
                "skill_id": r.skill_id,
                "skill_name": r.skill.name,
                "min_proficiency": r.min_proficiency,
                "required_count": r.required_count,
            }
            for r in m.requirements.all()
        ]

    def get_history(self, m):
        return [
            {
                "from_status": t.from_status,
                "to_status": t.to_status,
                "actor_name": t.actor.name,
                "reason": t.reason,
                "created_at": t.created_at,
            }
            for t in m.transitions.all()
        ]


class MissionListCreateApi(APIView):
    class InputSerializer(serializers.Serializer):
        name = serializers.CharField(max_length=255)
        description = serializers.CharField(allow_blank=True, required=False, default="")
        start_date = serializers.DateField()
        end_date = serializers.DateField()
        min_crew = serializers.IntegerField(min_value=1)
        max_crew = serializers.IntegerField(min_value=1)

    def get(self, request):
        ensure_permission(request.user, Permission.MISSION_VIEW)
        queryset = selectors.mission_list(
            status=request.query_params.get("status"),
            search=request.query_params.get("search"),
        )
        return get_paginated_response(
            serializer_class=MissionListItemSerializer, queryset=queryset, request=request
        )

    def post(self, request):
        ensure_permission(request.user, Permission.MISSION_CREATE)
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mission = services.mission_create(actor=request.user, **serializer.validated_data)
        mission = selectors.mission_get(mission.id)
        return Response(MissionDetailSerializer(mission).data, status=status.HTTP_201_CREATED)


class MissionDetailApi(APIView):
    class InputSerializer(serializers.Serializer):
        name = serializers.CharField(max_length=255, required=False)
        description = serializers.CharField(allow_blank=True, required=False)
        start_date = serializers.DateField(required=False)
        end_date = serializers.DateField(required=False)
        min_crew = serializers.IntegerField(min_value=1, required=False)
        max_crew = serializers.IntegerField(min_value=1, required=False)

    def get(self, request, mission_id: int):
        ensure_permission(request.user, Permission.MISSION_VIEW)
        mission = selectors.mission_get(mission_id)
        return Response(MissionDetailSerializer(mission).data)

    def patch(self, request, mission_id: int):
        ensure_permission(request.user, Permission.MISSION_EDIT)
        mission = selectors.mission_get(mission_id)
        serializer = self.InputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        services.mission_update(actor=request.user, mission=mission, **serializer.validated_data)
        mission = selectors.mission_get(mission_id)
        return Response(MissionDetailSerializer(mission).data)


class MissionRequirementItemSerializer(serializers.Serializer):
    # All three fields are required: `mission_requirements_set` reads
    # item["skill_id"], item["min_proficiency"], item["required_count"] directly, so a
    # missing field here must fail validation (400) rather than raise KeyError (500).
    skill_id = serializers.IntegerField()
    min_proficiency = serializers.IntegerField(min_value=1, max_value=10)
    required_count = serializers.IntegerField(min_value=1)


class MissionRequirementsApi(APIView):
    class InputSerializer(serializers.Serializer):
        items = MissionRequirementItemSerializer(many=True)

    def put(self, request, mission_id: int):
        ensure_permission(request.user, Permission.MISSION_EDIT)
        mission = selectors.mission_get(mission_id)
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.mission_requirements_set(
            actor=request.user, mission=mission, items=serializer.validated_data["items"]
        )
        mission = selectors.mission_get(mission_id)
        return Response(MissionDetailSerializer(mission).data)


class MissionTransitionApi(APIView):
    class InputSerializer(serializers.Serializer):
        action = serializers.CharField()
        reason = serializers.CharField(required=False, allow_blank=True)

    def post(self, request, mission_id: int):
        # No static permission check here: the FSM table (transition_mission) owns the
        # permission, ownership, and state-validity checks per action.
        mission = selectors.mission_get(mission_id)
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.transition_mission(
            actor=request.user, mission=mission, **serializer.validated_data
        )
        mission = selectors.mission_get(mission_id)
        return Response(MissionDetailSerializer(mission).data)
