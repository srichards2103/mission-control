from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from mission_control.common.pagination import get_paginated_response
from mission_control.users import selectors
from mission_control.users.permissions import Permission, ensure_permission


class CrewOutputSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    email = serializers.EmailField()
    skills = serializers.SerializerMethodField()

    def get_skills(self, user):
        return [
            {"skill_id": cs.skill_id, "name": cs.skill.name, "proficiency": cs.proficiency}
            for cs in user.crew_skills.all()
        ]


class CrewListApi(APIView):
    def get(self, request):
        ensure_permission(request.user, Permission.CREW_VIEW)
        return get_paginated_response(
            serializer_class=CrewOutputSerializer, queryset=selectors.crew_list(), request=request
        )


class CrewDetailApi(APIView):
    def get(self, request, user_id: int):
        ensure_permission(request.user, Permission.CREW_VIEW)
        return Response(CrewOutputSerializer(selectors.crew_get(user_id)).data)
