import pytest

from mission_control.users.factories import CrewSkillFactory, SkillFactory, UserFactory
from mission_control.users.models import CrewSkill
from mission_control.users.roles import Role

pytestmark = pytest.mark.django_db


def test_put_replaces_profile(auth_client_for):
    crew = UserFactory(role=Role.CREW_MEMBER)
    old = CrewSkillFactory(user=crew)
    s1, s2 = SkillFactory(tenant=crew.tenant), SkillFactory(tenant=crew.tenant)
    client = auth_client_for(crew)
    resp = client.put("/api/v1/me/skills/", {"items": [
        {"skill_id": s1.id, "proficiency": 7}, {"skill_id": s2.id, "proficiency": 3},
    ]}, format="json")
    assert resp.status_code == 200
    rows = CrewSkill.objects_unscoped.filter(user=crew)
    assert {(r.skill_id, r.proficiency) for r in rows} == {(s1.id, 7), (s2.id, 3)}
    assert not rows.filter(skill=old.skill).exists()


def test_archived_skill_rejected(auth_client_for):
    crew = UserFactory(role=Role.CREW_MEMBER)
    archived = SkillFactory(tenant=crew.tenant, is_archived=True)
    resp = auth_client_for(crew).put("/api/v1/me/skills/",
        {"items": [{"skill_id": archived.id, "proficiency": 5}]}, format="json")
    assert resp.status_code == 400


def test_out_of_range_proficiency_rejected(auth_client_for):
    crew = UserFactory(role=Role.CREW_MEMBER)
    skill = SkillFactory(tenant=crew.tenant)
    resp = auth_client_for(crew).put("/api/v1/me/skills/",
        {"items": [{"skill_id": skill.id, "proficiency": 11}]}, format="json")
    assert resp.status_code == 400


def test_directors_cannot_edit_profile(auth_client_for):
    director = UserFactory(role=Role.DIRECTOR)
    resp = auth_client_for(director).put("/api/v1/me/skills/", {"items": []}, format="json")
    assert resp.status_code == 403


def test_duplicate_skill_ids_in_payload_rejected(auth_client_for):
    crew = UserFactory(role=Role.CREW_MEMBER)
    skill = SkillFactory(tenant=crew.tenant)
    resp = auth_client_for(crew).put("/api/v1/me/skills/", {"items": [
        {"skill_id": skill.id, "proficiency": 3}, {"skill_id": skill.id, "proficiency": 7},
    ]}, format="json")
    assert resp.status_code == 400
    assert not CrewSkill.objects_unscoped.filter(user=crew, skill=skill).exists()


def test_cross_tenant_skill_id_rejected_not_500(auth_client_for):
    crew = UserFactory(role=Role.CREW_MEMBER)
    other_tenant_skill = SkillFactory()  # different tenant via factory default
    resp = auth_client_for(crew).put("/api/v1/me/skills/",
        {"items": [{"skill_id": other_tenant_skill.id, "proficiency": 5}]}, format="json")
    assert resp.status_code == 400
    assert not CrewSkill.objects_unscoped.filter(user=crew).exists()


def test_get_returns_own_profile_ordered_by_skill_name(auth_client_for):
    crew = UserFactory(role=Role.CREW_MEMBER)
    zeta_skill = SkillFactory(tenant=crew.tenant, name="Zeta")
    alpha_skill = SkillFactory(tenant=crew.tenant, name="Alpha")
    zeta = CrewSkillFactory(user=crew, skill=zeta_skill, proficiency=4)
    alpha = CrewSkillFactory(user=crew, skill=alpha_skill, proficiency=9)
    resp = auth_client_for(crew).get("/api/v1/me/skills/")
    assert resp.status_code == 200
    assert resp.data["items"] == [
        {"skill_id": alpha.skill_id, "skill_name": "Alpha", "proficiency": 9},
        {"skill_id": zeta.skill_id, "skill_name": "Zeta", "proficiency": 4},
    ]


def test_put_replaces_only_actors_own_rows_not_other_users(auth_client_for):
    crew = UserFactory(role=Role.CREW_MEMBER)
    other_crew = UserFactory(role=Role.CREW_MEMBER, tenant=crew.tenant)
    other_row = CrewSkillFactory(user=other_crew)
    skill = SkillFactory(tenant=crew.tenant)
    resp = auth_client_for(crew).put("/api/v1/me/skills/",
        {"items": [{"skill_id": skill.id, "proficiency": 6}]}, format="json")
    assert resp.status_code == 200
    other_row.refresh_from_db()
    assert other_row.proficiency == 5
