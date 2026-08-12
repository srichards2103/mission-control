import pytest

from mission_control.missions.factories import MissionFactory, MissionRequirementFactory
from mission_control.users.factories import UserFactory
from mission_control.users.roles import Role

pytestmark = pytest.mark.django_db


def test_lead_creates_mission(auth_client_for):
    lead = UserFactory(role=Role.MISSION_LEAD)
    resp = auth_client_for(lead).post("/api/v1/missions/", {
        "name": "Ganymede Survey", "start_date": "2026-09-01", "end_date": "2026-09-14",
        "min_crew": 2, "max_crew": 4,
    })
    assert resp.status_code == 201
    assert resp.data["status"] == "draft"


def test_crew_cannot_list_missions(auth_client_for):
    crew = UserFactory(role=Role.CREW_MEMBER)
    assert auth_client_for(crew).get("/api/v1/missions/").status_code == 403


def test_status_filter(auth_client_for):
    lead = UserFactory(role=Role.MISSION_LEAD)
    MissionFactory(tenant=lead.tenant, created_by=lead, status="active", name="Live one")
    MissionFactory(tenant=lead.tenant, created_by=lead, name="Draft one")
    resp = auth_client_for(lead).get("/api/v1/missions/?status=active")
    assert [m["name"] for m in resp.data["results"]] == ["Live one"]


def test_cross_tenant_mission_404(auth_client_for):
    lead = UserFactory(role=Role.MISSION_LEAD)
    other = MissionFactory()  # other tenant
    assert auth_client_for(lead).get(f"/api/v1/missions/{other.id}/").status_code == 404


def test_full_lifecycle_via_api(auth_client_for):
    lead = UserFactory(role=Role.MISSION_LEAD)
    director = UserFactory(role=Role.DIRECTOR, tenant=lead.tenant)
    mission = MissionFactory(tenant=lead.tenant, created_by=lead)
    MissionRequirementFactory(mission=mission)
    lead_client, director_client = auth_client_for(lead), auth_client_for(director)

    url = f"/api/v1/missions/{mission.id}/transitions/"
    assert lead_client.post(url, {"action": "submit"}).status_code == 200
    resp = director_client.post(url, {"action": "reject", "reason": "Dates clash with resupply"})
    assert resp.status_code == 200 and resp.data["status"] == "rejected"
    assert lead_client.post(url, {"action": "revise"}).status_code == 200
    resp = lead_client.get(f"/api/v1/missions/{mission.id}/")
    assert [h["to_status"] for h in resp.data["history"]] == [
        "draft",
        "rejected",
        "pending_approval",
    ]


def test_requirements_put(auth_client_for):
    from mission_control.users.factories import SkillFactory
    lead = UserFactory(role=Role.MISSION_LEAD)
    mission = MissionFactory(tenant=lead.tenant, created_by=lead)
    skill = SkillFactory(tenant=lead.tenant)
    resp = auth_client_for(lead).put(f"/api/v1/missions/{mission.id}/requirements/", {
        "items": [{"skill_id": skill.id, "min_proficiency": 6, "required_count": 2}],
    }, format="json")
    assert resp.status_code == 200
    assert resp.data["requirements"][0]["min_proficiency"] == 6
    # Persistence check via a fresh GET (real HTTP round-trip) rather than the ORM,
    # since the tenant context set for this request is gone once the response returns.
    resp = auth_client_for(lead).get(f"/api/v1/missions/{mission.id}/")
    assert len(resp.data["requirements"]) == 1


# --- Obligation from Task 3.2's review: mission_requirements_set reads
# item["skill_id"], item["min_proficiency"], item["required_count"] directly from each
# dict, so a malformed item would raise KeyError -> 500 unless the API serializer makes
# all three fields required. One test per missing field.


def test_requirements_put_missing_skill_id_is_400(auth_client_for):
    lead = UserFactory(role=Role.MISSION_LEAD)
    mission = MissionFactory(tenant=lead.tenant, created_by=lead)
    resp = auth_client_for(lead).put(f"/api/v1/missions/{mission.id}/requirements/", {
        "items": [{"min_proficiency": 6, "required_count": 2}],
    }, format="json")
    assert resp.status_code == 400
    assert resp.data["message"] == "Validation error"
    assert "skill_id" in resp.data["extra"]["fields"]["items"][0]


def test_requirements_put_missing_min_proficiency_is_400(auth_client_for):
    lead = UserFactory(role=Role.MISSION_LEAD)
    mission = MissionFactory(tenant=lead.tenant, created_by=lead)
    resp = auth_client_for(lead).put(f"/api/v1/missions/{mission.id}/requirements/", {
        "items": [{"skill_id": 1, "required_count": 2}],
    }, format="json")
    assert resp.status_code == 400
    assert resp.data["message"] == "Validation error"
    assert "min_proficiency" in resp.data["extra"]["fields"]["items"][0]


def test_requirements_put_missing_required_count_is_400(auth_client_for):
    lead = UserFactory(role=Role.MISSION_LEAD)
    mission = MissionFactory(tenant=lead.tenant, created_by=lead)
    resp = auth_client_for(lead).put(f"/api/v1/missions/{mission.id}/requirements/", {
        "items": [{"skill_id": 1, "min_proficiency": 6}],
    }, format="json")
    assert resp.status_code == 400
    assert resp.data["message"] == "Validation error"
    assert "required_count" in resp.data["extra"]["fields"]["items"][0]


def test_requirements_put_cross_tenant_404(auth_client_for):
    lead = UserFactory(role=Role.MISSION_LEAD)
    other = MissionFactory()  # other tenant
    resp = auth_client_for(lead).put(f"/api/v1/missions/{other.id}/requirements/", {
        "items": [],
    }, format="json")
    assert resp.status_code == 404


def test_crew_cannot_create_mission(auth_client_for):
    crew = UserFactory(role=Role.CREW_MEMBER)
    resp = auth_client_for(crew).post("/api/v1/missions/", {
        "name": "Nope", "start_date": "2026-09-01", "end_date": "2026-09-14",
        "min_crew": 1, "max_crew": 2,
    })
    assert resp.status_code == 403


def test_mission_patch_updates_and_persists(auth_client_for):
    lead = UserFactory(role=Role.MISSION_LEAD)
    mission = MissionFactory(tenant=lead.tenant, created_by=lead, name="Old name")
    resp = auth_client_for(lead).patch(
        f"/api/v1/missions/{mission.id}/", {"name": "New name"}, format="json"
    )
    assert resp.status_code == 200
    assert resp.data["name"] == "New name"
    mission.refresh_from_db()
    assert mission.name == "New name"


def test_patch_cross_tenant_404(auth_client_for):
    lead = UserFactory(role=Role.MISSION_LEAD)
    other = MissionFactory()  # other tenant
    resp = auth_client_for(lead).patch(
        f"/api/v1/missions/{other.id}/", {"name": "Hijack"}, format="json"
    )
    assert resp.status_code == 404


def test_crew_cannot_patch_mission(auth_client_for):
    lead = UserFactory(role=Role.MISSION_LEAD)
    crew = UserFactory(role=Role.CREW_MEMBER, tenant=lead.tenant)
    mission = MissionFactory(tenant=lead.tenant, created_by=lead)
    resp = auth_client_for(crew).patch(
        f"/api/v1/missions/{mission.id}/", {"name": "Nope"}, format="json"
    )
    assert resp.status_code == 403
    mission.refresh_from_db()
    assert mission.name != "Nope"


def test_transition_permission_denied_stays_403(auth_client_for):
    """The FSM table owns permissions -- crew lacks mission.progress, so submit 403s."""
    lead = UserFactory(role=Role.MISSION_LEAD)
    crew = UserFactory(role=Role.CREW_MEMBER, tenant=lead.tenant)
    mission = MissionFactory(tenant=lead.tenant, created_by=lead)
    MissionRequirementFactory(mission=mission)
    resp = auth_client_for(crew).post(
        f"/api/v1/missions/{mission.id}/transitions/", {"action": "submit"}
    )
    assert resp.status_code == 403
    mission.refresh_from_db()
    assert mission.status == "draft"


def test_transition_illegal_action_stays_400_envelope(auth_client_for):
    """A domain-rule failure (approve on a draft mission) surfaces as the 400 envelope."""
    lead = UserFactory(role=Role.MISSION_LEAD)
    director = UserFactory(role=Role.DIRECTOR, tenant=lead.tenant)
    mission = MissionFactory(tenant=lead.tenant, created_by=lead)
    resp = auth_client_for(director).post(
        f"/api/v1/missions/{mission.id}/transitions/", {"action": "approve"}
    )
    assert resp.status_code == 400
    assert resp.data["message"] == "Cannot approve a mission in state 'draft'."
    assert resp.data["extra"] == {}


def test_transition_cross_tenant_404(auth_client_for):
    lead = UserFactory(role=Role.MISSION_LEAD)
    other = MissionFactory()  # other tenant
    resp = auth_client_for(lead).post(
        f"/api/v1/missions/{other.id}/transitions/", {"action": "submit"}
    )
    assert resp.status_code == 404


def test_mission_list_pagination_envelope(auth_client_for):
    lead = UserFactory(role=Role.MISSION_LEAD)
    MissionFactory(tenant=lead.tenant, created_by=lead)
    resp = auth_client_for(lead).get("/api/v1/missions/")
    assert resp.status_code == 200
    assert set(resp.data.keys()) == {"results", "count", "limit", "offset"}


def test_mission_detail_permission_denied_stays_403(auth_client_for):
    crew = UserFactory(role=Role.CREW_MEMBER)
    mission = MissionFactory(tenant=crew.tenant)
    resp = auth_client_for(crew).get(f"/api/v1/missions/{mission.id}/")
    assert resp.status_code == 403


def test_transitions_endpoint_is_not_an_existence_oracle(auth_client_for):
    """I6: the transitions endpoint delegated ALL permission logic to
    `transition_mission`, which is right for the per-action permission but meant the
    fetch ran first -- so a crew member got 404 for a nonexistent mission id and 403 for
    a real one, an intra-tenant existence oracle. A MISSION_VIEW check before the fetch
    makes both answers identical; every role that can legally transition holds it.
    """
    lead = UserFactory(role=Role.MISSION_LEAD)
    crew = UserFactory(role=Role.CREW_MEMBER, tenant=lead.tenant)
    real = MissionFactory(tenant=lead.tenant, created_by=lead)
    client = auth_client_for(crew)

    real_resp = client.post(f"/api/v1/missions/{real.id}/transitions/", {"action": "submit"})
    missing_resp = client.post("/api/v1/missions/99999999/transitions/", {"action": "submit"})
    assert real_resp.status_code == missing_resp.status_code == 403
    assert real_resp.data == missing_resp.data
