import pytest
from rest_framework.test import APIClient

from mission_control.tenants.context import reset_current_tenant_id, set_current_tenant_id

TEST_PASSWORD = "password123"


@pytest.fixture(autouse=True)
def _clean_tenant_context():
    """Ensure every test starts and ends with no tenant in context.

    Guards against tenant context leaking between tests (e.g. a test that sets a
    tenant and forgets to reset it, or a prior test's failure skipping cleanup).
    """
    token = set_current_tenant_id(None)
    yield
    reset_current_tenant_id(token)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client_for(api_client):
    """Authenticate via the real JWT flow so the tenant context is set per-request."""

    def _make(user):
        resp = api_client.post(
            "/api/v1/auth/token/", {"email": user.email, "password": TEST_PASSWORD}
        )
        assert resp.status_code == 200, resp.content
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
        return client

    return _make
