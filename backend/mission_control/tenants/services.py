from rest_framework.exceptions import PermissionDenied

from mission_control.tenants.models import Tenant


def tenant_update(*, actor, tenant: Tenant, name: str) -> Tenant:
    # `Tenant` is the one model with no fail-closed manager -- it is the tenancy root,
    # so nothing scopes it. Without this assertion the service is a bare cross-tenant
    # write primitive that happens to be safe only because its single caller passes
    # `request.user.tenant`. Assert the invariant here, where it belongs.
    if tenant.id != actor.tenant_id:
        raise PermissionDenied("You can only manage your own organisation.")
    tenant.name = name
    tenant.full_clean()
    tenant.save()
    return tenant
