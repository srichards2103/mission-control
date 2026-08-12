from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from mission_control.common.pagination import get_paginated_response
from mission_control.tenants import services as tenant_services
from mission_control.users import selectors, services
from mission_control.users.permissions import Permission, ensure_permission
from mission_control.users.roles import Role


class SettingsUserOutputSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    email = serializers.EmailField()
    role = serializers.CharField()
    is_active = serializers.BooleanField()


class SettingsUserListCreateApi(APIView):
    class InputSerializer(serializers.Serializer):
        email = serializers.EmailField()
        name = serializers.CharField(max_length=255)
        role = serializers.ChoiceField(choices=Role.choices)
        password = serializers.CharField(min_length=8, write_only=True)

    def get(self, request):
        ensure_permission(request.user, Permission.USER_MANAGE)
        return get_paginated_response(
            serializer_class=SettingsUserOutputSerializer,
            queryset=selectors.user_list(),
            request=request,
        )

    def post(self, request):
        ensure_permission(request.user, Permission.USER_MANAGE)
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.user_create(actor=request.user, **serializer.validated_data)
        return Response(SettingsUserOutputSerializer(user).data, status=status.HTTP_201_CREATED)


class SettingsUserUpdateApi(APIView):
    class InputSerializer(serializers.Serializer):
        role = serializers.ChoiceField(choices=Role.choices, required=False)
        is_active = serializers.BooleanField(required=False)

    def patch(self, request, user_id: int):
        ensure_permission(request.user, Permission.USER_MANAGE)
        user = selectors.user_get(user_id)
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.user_update(actor=request.user, user=user, **serializer.validated_data)
        return Response(SettingsUserOutputSerializer(user).data)


class OrganisationApi(APIView):
    class InputSerializer(serializers.Serializer):
        name = serializers.CharField(max_length=255)

    class OutputSerializer(serializers.Serializer):
        id = serializers.IntegerField()
        name = serializers.CharField()
        slug = serializers.CharField()

    def get(self, request):
        ensure_permission(request.user, Permission.SETTINGS_VIEW)
        return Response(self.OutputSerializer(request.user.tenant).data)

    def patch(self, request):
        ensure_permission(request.user, Permission.SETTINGS_MANAGE)
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tenant = tenant_services.tenant_update(
            actor=request.user, tenant=request.user.tenant, **serializer.validated_data
        )
        return Response(self.OutputSerializer(tenant).data)
