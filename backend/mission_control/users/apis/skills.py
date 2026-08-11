from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from mission_control.common.pagination import get_paginated_response
from mission_control.users import selectors, services
from mission_control.users.permissions import Permission, ensure_permission


class SkillOutputSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    description = serializers.CharField()
    is_archived = serializers.BooleanField()


class SkillListCreateApi(APIView):
    class InputSerializer(serializers.Serializer):
        name = serializers.CharField(max_length=100)
        description = serializers.CharField(allow_blank=True, required=False, default="")

    def get(self, request):
        ensure_permission(request.user, Permission.SKILL_VIEW)
        return get_paginated_response(
            serializer_class=SkillOutputSerializer, queryset=selectors.skill_list(), request=request
        )

    def post(self, request):
        ensure_permission(request.user, Permission.SKILL_MANAGE)
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        skill = services.skill_create(actor=request.user, **serializer.validated_data)
        return Response(SkillOutputSerializer(skill).data, status=status.HTTP_201_CREATED)


class SkillUpdateApi(APIView):
    class InputSerializer(serializers.Serializer):
        name = serializers.CharField(max_length=100, required=False)
        description = serializers.CharField(allow_blank=True, required=False)
        is_archived = serializers.BooleanField(required=False)

    def patch(self, request, skill_id: int):
        ensure_permission(request.user, Permission.SKILL_MANAGE)
        skill = selectors.skill_get(skill_id)
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        skill = services.skill_update(actor=request.user, skill=skill, **serializer.validated_data)
        return Response(SkillOutputSerializer(skill).data)
