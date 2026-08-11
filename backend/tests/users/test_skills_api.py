import pytest

from mission_control.users.factories import SkillFactory, UserFactory
from mission_control.users.roles import Role

pytestmark = pytest.mark.django_db


def test_director_creates_skill(auth_client_for):
    director = UserFactory(role=Role.DIRECTOR)
    client = auth_client_for(director)
    resp = client.post("/api/v1/skills/", {"name": "EVA Ops", "description": "Spacewalks"})
    assert resp.status_code == 201
    assert resp.data["name"] == "EVA Ops"


def test_duplicate_name_case_insensitive_400(auth_client_for):
    director = UserFactory(role=Role.DIRECTOR)
    SkillFactory(tenant=director.tenant, name="Piloting")
    resp = auth_client_for(director).post("/api/v1/skills/", {"name": "piloting"})
    assert resp.status_code == 400
    assert resp.data["message"] == "Validation error"


def test_lead_cannot_manage_but_can_view(auth_client_for):
    lead = UserFactory(role=Role.MISSION_LEAD)
    SkillFactory(tenant=lead.tenant)
    client = auth_client_for(lead)
    assert client.post("/api/v1/skills/", {"name": "X"}).status_code == 403
    assert client.get("/api/v1/skills/").status_code == 200


def test_list_is_tenant_scoped(auth_client_for):
    lead = UserFactory(role=Role.MISSION_LEAD)
    SkillFactory(tenant=lead.tenant, name="Mine")
    SkillFactory(name="Other tenants")  # different tenant via factory default
    resp = auth_client_for(lead).get("/api/v1/skills/")
    assert [s["name"] for s in resp.data["results"]] == ["Mine"]


def test_cross_tenant_patch_is_404(auth_client_for):
    director = UserFactory(role=Role.DIRECTOR)
    other = SkillFactory()  # other tenant
    resp = auth_client_for(director).patch(f"/api/v1/skills/{other.id}/", {"name": "Hijack"})
    assert resp.status_code == 404
