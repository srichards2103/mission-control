import pytest

from mission_control.users.factories import CrewSkillFactory, UserFactory
from mission_control.users.roles import Role

pytestmark = pytest.mark.django_db


def test_crew_list_scoped_with_skills(auth_client_for):
    lead = UserFactory(role=Role.MISSION_LEAD)
    crew = UserFactory(role=Role.CREW_MEMBER, tenant=lead.tenant, name="Ada")
    CrewSkillFactory(user=crew, proficiency=8)
    UserFactory(role=Role.CREW_MEMBER)  # other tenant
    UserFactory(role=Role.DIRECTOR, tenant=lead.tenant)  # not crew
    resp = auth_client_for(lead).get("/api/v1/crew/")
    assert resp.status_code == 200
    assert [c["name"] for c in resp.data["results"]] == ["Ada"]
    assert resp.data["results"][0]["skills"][0]["proficiency"] == 8


def test_crew_member_cannot_view_directory(auth_client_for):
    crew = UserFactory(role=Role.CREW_MEMBER)
    assert auth_client_for(crew).get("/api/v1/crew/").status_code == 403


def test_cross_tenant_detail_404(auth_client_for):
    lead = UserFactory(role=Role.MISSION_LEAD)
    other = UserFactory(role=Role.CREW_MEMBER)  # other tenant
    assert auth_client_for(lead).get(f"/api/v1/crew/{other.id}/").status_code == 404


def test_crew_member_cannot_view_detail(auth_client_for):
    crew = UserFactory(role=Role.CREW_MEMBER)
    other = UserFactory(role=Role.CREW_MEMBER, tenant=crew.tenant)
    assert auth_client_for(crew).get(f"/api/v1/crew/{other.id}/").status_code == 403


def test_crew_detail_happy_path(auth_client_for):
    lead = UserFactory(role=Role.MISSION_LEAD)
    crew = UserFactory(role=Role.CREW_MEMBER, tenant=lead.tenant, name="Grace")
    CrewSkillFactory(user=crew, proficiency=6)
    resp = auth_client_for(lead).get(f"/api/v1/crew/{crew.id}/")
    assert resp.status_code == 200
    assert resp.data["name"] == "Grace"
    assert resp.data["skills"][0]["proficiency"] == 6
