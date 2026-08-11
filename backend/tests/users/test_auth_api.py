import pytest

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
