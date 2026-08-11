from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from mission_control.users.permissions import permissions_for_role


class MeApi(APIView):
    class OutputSerializer(serializers.Serializer):
        id = serializers.IntegerField()
        email = serializers.EmailField()
        name = serializers.CharField()
        role = serializers.CharField()
        tenant = serializers.SerializerMethodField()
        permissions = serializers.SerializerMethodField()

        def get_tenant(self, user):
            return {"id": user.tenant.id, "name": user.tenant.name, "slug": user.tenant.slug}

        def get_permissions(self, user):
            return sorted(p.value for p in permissions_for_role(user.role))

    def get(self, request):
        return Response(self.OutputSerializer(request.user).data)
