import pytest
from django.http import HttpResponse
from django.test import RequestFactory

from mission_control.tenants.context import (
    TenantContextNotSet,
    get_current_tenant_id,
    require_current_tenant_id,
    reset_current_tenant_id,
    set_current_tenant_id,
)
from mission_control.tenants.middleware import TenantContextMiddleware


def test_require_raises_when_unset():
    assert get_current_tenant_id() is None
    with pytest.raises(TenantContextNotSet):
        require_current_tenant_id()


def test_set_and_reset_roundtrip():
    token = set_current_tenant_id(42)
    assert require_current_tenant_id() == 42
    reset_current_tenant_id(token)
    assert get_current_tenant_id() is None


def test_middleware_clears_context_after_request():
    def view(request):
        set_current_tenant_id(7)  # what the JWT auth class will do
        assert get_current_tenant_id() == 7
        return HttpResponse()

    middleware = TenantContextMiddleware(view)
    middleware(RequestFactory().get("/"))
    assert get_current_tenant_id() is None
