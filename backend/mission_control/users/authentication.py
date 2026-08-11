from rest_framework_simplejwt.authentication import JWTAuthentication

from mission_control.tenants.context import set_current_tenant_id


class TenantJWTAuthentication(JWTAuthentication):
    """Binds the tenant context to the authenticated user for the rest of the request."""

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is not None:
            user, _token = result
            set_current_tenant_id(user.tenant_id)
        return result
