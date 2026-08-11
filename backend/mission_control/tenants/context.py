from contextvars import ContextVar, Token

_current_tenant_id: ContextVar[int | None] = ContextVar("current_tenant_id", default=None)


class TenantContextNotSet(Exception):
    """A tenant-scoped operation ran with no tenant in context. Fail closed."""


def set_current_tenant_id(tenant_id: int | None) -> Token:
    return _current_tenant_id.set(tenant_id)


def reset_current_tenant_id(token: Token) -> None:
    _current_tenant_id.reset(token)


def get_current_tenant_id() -> int | None:
    return _current_tenant_id.get()


def require_current_tenant_id() -> int:
    tenant_id = _current_tenant_id.get()
    if tenant_id is None:
        raise TenantContextNotSet("No tenant in context; refusing unscoped access to tenant data.")
    return tenant_id
