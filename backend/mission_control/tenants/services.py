from mission_control.tenants.models import Tenant


def tenant_update(*, actor, tenant: Tenant, name: str) -> Tenant:
    tenant.name = name
    tenant.full_clean()
    tenant.save()
    return tenant
