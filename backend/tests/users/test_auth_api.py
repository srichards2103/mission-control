import pytest
from rest_framework_simplejwt.tokens import RefreshToken

from mission_control.tenants.context import get_current_tenant_id
from mission_control.users.authentication import TenantJWTAuthentication
from mission_control.users.factories import UserFactory
from mission_control.users.roles import Role

pytestmark = pytest.mark.django_db


def test_token_obtain_and_me(api_client, auth_client_for):
    user = UserFactory(role=Role.MISSION_LEAD)
    client = auth_client_for(user)
    resp = client.get("/api/v1/auth/me/")
    assert resp.status_code == 200
    assert resp.data["email"] == user.email
    assert resp.data["role"] == "mission_lead"
    assert resp.data["tenant"]["slug"] == user.tenant.slug
    assert "mission.create" in resp.data["permissions"]
    assert "mission.review" not in resp.data["permissions"]


def test_bad_password_gets_envelope(api_client):
    user = UserFactory()
    resp = api_client.post("/api/v1/auth/token/", {"email": user.email, "password": "wrong"})
    assert resp.status_code == 401
    assert set(resp.data) == {"message", "extra"}


def test_me_requires_auth(api_client):
    assert api_client.get("/api/v1/auth/me/").status_code == 401


def test_inactive_user_cannot_obtain_token(api_client):
    user = UserFactory(is_active=False)
    resp = api_client.post(
        "/api/v1/auth/token/", {"email": user.email, "password": "password123"}
    )
    assert resp.status_code == 401


def test_authenticate_binds_tenant_context_from_token(rf):
    # Pins the actual point of TenantJWTAuthentication: that a successful
    # authenticate() call sets the tenant context from the resolved user's tenant.
    # Deleting the `set_current_tenant_id(...)` line in authentication.py must fail
    # this test even though /auth/me/ itself wouldn't notice (Tenant isn't a
    # TenantModel, so serializing it never consults the context).
    user = UserFactory()
    access_token = str(RefreshToken.for_user(user).access_token)
    request = rf.get("/api/v1/auth/me/", HTTP_AUTHORIZATION=f"Bearer {access_token}")

    result = TenantJWTAuthentication().authenticate(request)

    assert result is not None
    authenticated_user, _token = result
    assert authenticated_user.id == user.id
    assert get_current_tenant_id() == user.tenant_id


def test_authenticate_without_credentials_leaves_tenant_context_unset(rf):
    request = rf.get("/api/v1/auth/me/")

    result = TenantJWTAuthentication().authenticate(request)

    assert result is None
    assert get_current_tenant_id() is None


def test_invalid_bearer_token_gets_clean_message(api_client):
    resp = api_client.get("/api/v1/auth/me/", HTTP_AUTHORIZATION="Bearer garbage-token")
    assert resp.status_code == 401
    assert resp.data["message"] == "Given token not valid for any token type"
    assert "ErrorDetail" not in resp.data["message"]
