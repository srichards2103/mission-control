import datetime as dt

import pytest

from mission_control.missions.factories import (
    AssignmentFactory,
    MissionFactory,
    MissionRequirementFactory,
)
from mission_control.missions.models import AssignmentStatus, MissionStatus
from mission_control.users.factories import CrewSkillFactory, SkillFactory, UserFactory
from mission_control.users.roles import Role

pytestmark = pytest.mark.django_db

TODAY = dt.date.today()


def test_director_gets_dashboard_with_all_four_keys(auth_client_for):
    director = UserFactory(role=Role.DIRECTOR)
    resp = auth_client_for(director).get("/api/v1/dashboard/")
    assert resp.status_code == 200
    assert set(resp.data.keys()) == {"pipeline", "readiness", "utilization", "skill_gaps"}


def test_crew_member_forbidden(auth_client_for):
    crew = UserFactory(role=Role.CREW_MEMBER)
    resp = auth_client_for(crew).get("/api/v1/dashboard/")
    assert resp.status_code == 403


def test_empty_organisation_shape(auth_client_for):
    """No missions/crew at all -- every selector renders empty, not an error."""
    director = UserFactory(role=Role.DIRECTOR)
    resp = auth_client_for(director).get("/api/v1/dashboard/")
    assert resp.status_code == 200
    assert resp.data["pipeline"]["status_counts"] == {s: 0 for s in MissionStatus.values}
    assert resp.data["pipeline"]["pending_approvals"] == []
    assert resp.data["pipeline"]["upcoming"] == []
    assert resp.data["readiness"] == []
    assert resp.data["utilization"] == {"window_days": 90, "org_utilization_pct": 0, "crew": []}
    assert resp.data["skill_gaps"] == []


def test_response_shape_with_data(auth_client_for):
    director = UserFactory(role=Role.DIRECTOR)
    lead = UserFactory(role=Role.MISSION_LEAD, tenant=director.tenant)
    skill = SkillFactory(tenant=director.tenant, name="Piloting")

    mission = MissionFactory(
        tenant=director.tenant,
        created_by=lead,
        status=MissionStatus.APPROVED,
        start_date=TODAY + dt.timedelta(days=5),
        end_date=TODAY + dt.timedelta(days=15),
        min_crew=2,
        max_crew=4,
    )
    MissionRequirementFactory(mission=mission, skill=skill, min_proficiency=3, required_count=2)
    crew = UserFactory(role=Role.CREW_MEMBER, tenant=director.tenant, name="Crew One")
    CrewSkillFactory(user=crew, skill=skill, proficiency=8)
    AssignmentFactory(
        mission=mission, user=crew, status=AssignmentStatus.ACCEPTED, created_by=lead
    )

    resp = auth_client_for(director).get("/api/v1/dashboard/")
    assert resp.status_code == 200

    pipeline = resp.data["pipeline"]
    assert set(pipeline.keys()) == {"status_counts", "pending_approvals", "upcoming"}
    assert set(pipeline["status_counts"].keys()) == set(MissionStatus.values)
    assert pipeline["status_counts"]["approved"] == 1

    readiness = resp.data["readiness"]
    assert len(readiness) == 1
    row = readiness[0]
    assert set(row.keys()) == {
        "mission_id", "name", "status", "start_date", "coverage_pct",
        "accepted_count", "min_crew", "fully_covered", "at_risk",
    }
    assert row["mission_id"] == mission.id
    assert row["accepted_count"] == 1

    utilization = resp.data["utilization"]
    assert set(utilization.keys()) == {"window_days", "org_utilization_pct", "crew"}
    assert utilization["window_days"] == 90
    crew_row = utilization["crew"][0]
    assert set(crew_row.keys()) == {"user_id", "name", "assigned_days", "utilization_pct"}
    assert crew_row["user_id"] == crew.id
    assert crew_row["name"] == "Crew One"

    gaps = resp.data["skill_gaps"]
    assert len(gaps) == 1
    gap_row = gaps[0]
    assert set(gap_row.keys()) == {"skill_id", "skill_name", "open_seats", "qualified_crew", "gap"}
    assert gap_row["skill_name"] == "Piloting"
    assert gap_row["open_seats"] == 2
    assert gap_row["qualified_crew"] == 1
    assert gap_row["gap"] is True
