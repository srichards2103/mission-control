import datetime as dt

import pytest

from mission_control.missions.factories import MissionFactory, MissionRequirementFactory
from mission_control.users.factories import CrewSkillFactory, SkillFactory, UserFactory
from mission_control.users.roles import Role

pytestmark = pytest.mark.django_db


def test_match_returns_team_and_makes_no_assignments(auth_client_for):
    lead = UserFactory(role=Role.MISSION_LEAD)
    mission = MissionFactory(tenant=lead.tenant, created_by=lead,
                             start_date=dt.date(2026, 9, 1), end_date=dt.date(2026, 9, 10))
    skill = SkillFactory(tenant=lead.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=skill, min_proficiency=5)
    crew = UserFactory(role=Role.CREW_MEMBER, tenant=lead.tenant)
    CrewSkillFactory(user=crew, skill=skill, proficiency=8)

    resp = auth_client_for(lead).post(f"/api/v1/missions/{mission.id}/match/")
    assert resp.status_code == 200
    assert resp.data["team"][0]["user_id"] == crew.id
    from mission_control.missions.models import Assignment
    assert Assignment.objects_unscoped.count() == 0  # pure


def test_crew_cannot_run_matcher(auth_client_for):
    crew = UserFactory(role=Role.CREW_MEMBER)
    mission = MissionFactory(tenant=crew.tenant)
    assert auth_client_for(crew).post(f"/api/v1/missions/{mission.id}/match/").status_code == 403


def test_match_terminal_mission_400(auth_client_for):
    lead = UserFactory(role=Role.MISSION_LEAD)
    mission = MissionFactory(tenant=lead.tenant, created_by=lead, status="completed")
    assert auth_client_for(lead).post(f"/api/v1/missions/{mission.id}/match/").status_code == 400


def test_cross_tenant_mission_404(auth_client_for):
    lead = UserFactory(role=Role.MISSION_LEAD)
    other = MissionFactory()  # other tenant
    resp = auth_client_for(lead).post(f"/api/v1/missions/{other.id}/match/")
    assert resp.status_code == 404


def test_response_shape_matches_dataclass_field_names(auth_client_for):
    lead = UserFactory(role=Role.MISSION_LEAD)
    mission = MissionFactory(
        tenant=lead.tenant,
        created_by=lead,
        start_date=dt.date(2026, 9, 1),
        end_date=dt.date(2026, 9, 10),
        min_crew=1,
        max_crew=1,
    )
    skill = SkillFactory(tenant=lead.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=skill, min_proficiency=5)
    crew = UserFactory(role=Role.CREW_MEMBER, tenant=lead.tenant, name="Crew One")
    CrewSkillFactory(user=crew, skill=skill, proficiency=8)

    resp = auth_client_for(lead).post(f"/api/v1/missions/{mission.id}/match/")
    assert resp.status_code == 200
    assert set(resp.data.keys()) == {"team", "unfilled_seats", "alternatives", "open_capacity"}

    member = resp.data["team"][0]
    assert set(member.keys()) == {
        "user_id", "name", "seats", "score", "breakdown", "workload_days", "soft_conflicts",
    }
    assert member["user_id"] == crew.id
    assert member["name"] == "Crew One"
    assert set(member["breakdown"].keys()) == {
        "proficiency_fit", "workload_balance", "soft_conflict_penalty",
    }
    assert member["seats"][0]["skill_name"] == "Piloting"

    for alt in resp.data["alternatives"]:
        assert set(alt.keys()) == {"requirement_id", "skill_name", "min_proficiency", "candidates"}
