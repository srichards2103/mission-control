import pytest
from rest_framework.test import APIClient

# The `_clean_tenant_context` autouse fixture (and its import of
# mission_control.tenants.context) is added in Task 1.2, once that package exists.
# A module-level import of a nonexistent package here would break collection for
# every test run, the same failure mode the settings.INSTALLED_APPS ruling avoids.

TEST_PASSWORD = "password123"


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
