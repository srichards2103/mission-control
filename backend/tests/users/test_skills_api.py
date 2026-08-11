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
    assert resp.data["count"] == 1
    assert resp.data["limit"] == 25
    assert resp.data["offset"] == 0


def test_cross_tenant_patch_is_404(auth_client_for):
    director = UserFactory(role=Role.DIRECTOR)
    other = SkillFactory()  # other tenant
    resp = auth_client_for(director).patch(f"/api/v1/skills/{other.id}/", {"name": "Hijack"})
    assert resp.status_code == 404


def test_same_tenant_patch_updates_and_persists(auth_client_for):
    director = UserFactory(role=Role.DIRECTOR)
    skill = SkillFactory(tenant=director.tenant, name="Piloting", is_archived=False)
    resp = auth_client_for(director).patch(
        f"/api/v1/skills/{skill.id}/", {"name": "Advanced Piloting", "is_archived": True}
    )
    assert resp.status_code == 200
    assert resp.data["name"] == "Advanced Piloting"
    assert resp.data["is_archived"] is True

    skill.refresh_from_db()
    assert skill.name == "Advanced Piloting"
    assert skill.is_archived is True


def test_lead_cannot_patch(auth_client_for):
    lead = UserFactory(role=Role.MISSION_LEAD)
    skill = SkillFactory(tenant=lead.tenant, name="Piloting")
    resp = auth_client_for(lead).patch(f"/api/v1/skills/{skill.id}/", {"name": "Hijack"})
    assert resp.status_code == 403
