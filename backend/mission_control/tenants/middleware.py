from mission_control.tenants.context import reset_current_tenant_id, set_current_tenant_id


class TenantContextMiddleware:
    """Guarantees the tenant context never leaks between requests (incl. on exceptions)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = set_current_tenant_id(None)
        try:
            return self.get_response(request)
        finally:
            reset_current_tenant_id(token)
