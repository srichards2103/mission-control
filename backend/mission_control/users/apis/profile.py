from rest_framework import serializers
from rest_framework.views import APIView

from mission_control.common.pagination import get_paginated_response
from mission_control.users import selectors, services
from mission_control.users.permissions import Permission, ensure_permission


class MySkillsApi(APIView):
    class ItemSerializer(serializers.Serializer):
        skill_id = serializers.IntegerField()
        proficiency = serializers.IntegerField(min_value=1, max_value=10)

    class OutputSerializer(serializers.Serializer):
        skill_id = serializers.IntegerField()
        skill_name = serializers.CharField(source="skill.name")
        proficiency = serializers.IntegerField()

    def get(self, request):
        ensure_permission(request.user, Permission.OWN_SKILLS_EDIT)
        rows = selectors.crew_skills_for_user(request.user)
        return get_paginated_response(
            serializer_class=self.OutputSerializer, queryset=rows, request=request
        )

    def put(self, request):
        ensure_permission(request.user, Permission.OWN_SKILLS_EDIT)
        items_serializer = self.ItemSerializer(data=request.data.get("items", []), many=True)
        items_serializer.is_valid(raise_exception=True)
        services.crew_skills_set(actor=request.user, items=items_serializer.validated_data)
        rows = selectors.crew_skills_for_user(request.user)
        return get_paginated_response(
            serializer_class=self.OutputSerializer, queryset=rows, request=request
        )
