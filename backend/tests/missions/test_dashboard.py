import datetime as dt

import pytest

from mission_control.missions.factories import (
    AssignmentFactory,
    MissionFactory,
    MissionRequirementFactory,
)
from mission_control.missions.models import AssignmentStatus, MissionStatus, MissionTransition
from mission_control.missions.selectors.dashboard import (
    crew_utilization,
    pipeline_summary,
    skill_gaps,
    staffing_readiness,
)
from mission_control.tenants.context import set_current_tenant_id
from mission_control.users.factories import (
    CrewSkillFactory,
    SkillFactory,
    TenantFactory,
    UserFactory,
)
from mission_control.users.roles import Role

pytestmark = pytest.mark.django_db
TODAY = dt.date.today()


@pytest.fixture
def tenant():
    t = TenantFactory()
    set_current_tenant_id(t.id)
    return t


# --------------------------------------------------------------------- empty organisation


def test_empty_organisation_returns_zeros_not_errors(tenant):
    summary = pipeline_summary()
    assert summary["status_counts"] == {status: 0 for status in MissionStatus.values}
    assert summary["pending_approvals"] == []
    assert summary["upcoming"] == []

    assert staffing_readiness() == []

    util = crew_utilization()
    assert util == {"window_days": 90, "org_utilization_pct": 0, "crew": []}

    assert skill_gaps() == []


# --------------------------------------------------------------------- pipeline_summary


def test_pipeline_counts_and_queue(tenant):
    lead = UserFactory(role=Role.MISSION_LEAD, tenant=tenant)
    MissionFactory(tenant=tenant, created_by=lead)  # draft
    pending = MissionFactory(
        tenant=tenant,
        created_by=lead,
        status=MissionStatus.PENDING_APPROVAL,
        start_date=TODAY + dt.timedelta(days=10),
        end_date=TODAY + dt.timedelta(days=20),
        name="Awaiting",
    )
    MissionTransition.objects_unscoped.create(
        tenant=tenant,
        mission=pending,
        from_status="draft",
        to_status="pending_approval",
        actor=lead,
        reason="",
    )
    summary = pipeline_summary()
    assert summary["status_counts"]["draft"] == 1
    assert summary["status_counts"]["pending_approval"] == 1
    assert summary["pending_approvals"][0]["name"] == "Awaiting"
    assert summary["pending_approvals"][0]["age_days"] == 0
    assert any(u["name"] == "Awaiting" for u in summary["upcoming"])


def test_pipeline_upcoming_excludes_missions_outside_30_day_window(tenant):
    lead = UserFactory(role=Role.MISSION_LEAD, tenant=tenant)
    MissionFactory(
        tenant=tenant,
        created_by=lead,
        status=MissionStatus.APPROVED,
        start_date=TODAY + dt.timedelta(days=31),
        end_date=TODAY + dt.timedelta(days=40),
        name="Too Far Out",
    )
    MissionFactory(
        tenant=tenant,
        created_by=lead,
        status=MissionStatus.APPROVED,
        start_date=TODAY - dt.timedelta(days=1),
        end_date=TODAY + dt.timedelta(days=5),
        name="Already Started",
    )
    MissionFactory(
        tenant=tenant,
        created_by=lead,
        status=MissionStatus.APPROVED,
        start_date=TODAY + dt.timedelta(days=30),
        end_date=TODAY + dt.timedelta(days=40),
        name="Exactly 30",
    )
    names = {u["name"] for u in pipeline_summary()["upcoming"]}
    assert names == {"Exactly 30"}


def test_pipeline_summary_query_count_is_constant(tenant, django_assert_num_queries):
    lead = UserFactory(role=Role.MISSION_LEAD, tenant=tenant)

    def make_missions(n):
        for i in range(n):
            m = MissionFactory(
                tenant=tenant,
                created_by=lead,
                status=MissionStatus.PENDING_APPROVAL,
                start_date=TODAY + dt.timedelta(days=i + 1),
                end_date=TODAY + dt.timedelta(days=i + 5),
                name=f"Pending {i}",
            )
            MissionTransition.objects_unscoped.create(
                tenant=tenant,
                mission=m,
                from_status="draft",
                to_status="pending_approval",
                actor=lead,
                reason="",
            )
            MissionFactory(tenant=tenant, created_by=lead)  # draft, adds to status_counts

    make_missions(2)
    with django_assert_num_queries(3):
        pipeline_summary()

    make_missions(8)
    with django_assert_num_queries(3):
        pipeline_summary()


# --------------------------------------------------------------------- staffing_readiness


def test_readiness_flags_understaffed(tenant):
    lead = UserFactory(role=Role.MISSION_LEAD, tenant=tenant)
    mission = MissionFactory(
        tenant=tenant,
        created_by=lead,
        status=MissionStatus.APPROVED,
        start_date=TODAY + dt.timedelta(days=5),
        end_date=TODAY + dt.timedelta(days=10),
        min_crew=2,
        max_crew=4,
    )
    skill = SkillFactory(tenant=tenant)
    MissionRequirementFactory(mission=mission, skill=skill, min_proficiency=5, required_count=2)
    crew = UserFactory(role=Role.CREW_MEMBER, tenant=tenant)
    CrewSkillFactory(user=crew, skill=skill, proficiency=8)
    AssignmentFactory(mission=mission, user=crew, status=AssignmentStatus.ACCEPTED)
    rows = staffing_readiness()
    assert rows[0]["coverage_pct"] == 50
    assert rows[0]["at_risk"] is True


def test_readiness_excludes_ended_and_irrelevant_statuses(tenant):
    lead = UserFactory(role=Role.MISSION_LEAD, tenant=tenant)
    MissionFactory(
        tenant=tenant,
        created_by=lead,
        status=MissionStatus.APPROVED,
        start_date=TODAY - dt.timedelta(days=20),
        end_date=TODAY - dt.timedelta(days=1),
        name="Already Ended",
    )
    MissionFactory(tenant=tenant, created_by=lead, status=MissionStatus.DRAFT, name="Still Draft")
    MissionFactory(
        tenant=tenant, created_by=lead, status=MissionStatus.COMPLETED, name="Done"
    )
    live = MissionFactory(
        tenant=tenant,
        created_by=lead,
        status=MissionStatus.ACTIVE,
        start_date=TODAY,
        end_date=TODAY + dt.timedelta(days=5),
        name="Live One",
    )
    rows = staffing_readiness()
    assert [r["mission_id"] for r in rows] == [live.id]


def test_readiness_fully_covered_and_at_risk_ordering(tenant):
    lead = UserFactory(role=Role.MISSION_LEAD, tenant=tenant)
    skill = SkillFactory(tenant=tenant)

    covered = MissionFactory(
        tenant=tenant,
        created_by=lead,
        status=MissionStatus.APPROVED,
        start_date=TODAY + dt.timedelta(days=20),
        end_date=TODAY + dt.timedelta(days=25),
        min_crew=1,
        max_crew=2,
        name="Covered",
    )
    MissionRequirementFactory(mission=covered, skill=skill, min_proficiency=1, required_count=1)
    covered_crew = UserFactory(role=Role.CREW_MEMBER, tenant=tenant)
    CrewSkillFactory(user=covered_crew, skill=skill, proficiency=5)
    AssignmentFactory(mission=covered, user=covered_crew, status=AssignmentStatus.ACCEPTED)

    risky = MissionFactory(
        tenant=tenant,
        created_by=lead,
        status=MissionStatus.APPROVED,
        start_date=TODAY + dt.timedelta(days=1),
        end_date=TODAY + dt.timedelta(days=2),
        min_crew=1,
        max_crew=2,
        name="Risky",
    )
    MissionRequirementFactory(mission=risky, skill=skill, min_proficiency=1, required_count=1)

    rows = staffing_readiness()
    assert [r["name"] for r in rows] == ["Risky", "Covered"]
    covered_row = next(r for r in rows if r["name"] == "Covered")
    assert covered_row["fully_covered"] is True
    assert covered_row["at_risk"] is False
    assert covered_row["coverage_pct"] == 100


def test_readiness_query_count_scales_with_relevant_missions_only(
    tenant, django_assert_num_queries
):
    """`staffing_readiness` calls mission_coverage (3 queries) once per relevant mission,
    plus 1 for the mission list itself: 1 + 3*N. This test proves that N is the count of
    *relevant* (live, not-ended) missions — irrelevant history (draft/completed/cancelled)
    added alongside does not change the query count for a fixed relevant count.
    """
    lead = UserFactory(role=Role.MISSION_LEAD, tenant=tenant)
    skill = SkillFactory(tenant=tenant)

    def make_relevant(n):
        # Give each mission a requirement + an accepted crew member so mission_coverage
        # takes its full 3-query path (it skips the crew-skill query when a mission has
        # no requirements or no accepted crew), matching the 1 + 3*N formula exactly.
        for i in range(n):
            mission = MissionFactory(
                tenant=tenant,
                created_by=lead,
                status=MissionStatus.APPROVED,
                start_date=TODAY + dt.timedelta(days=i + 1),
                end_date=TODAY + dt.timedelta(days=i + 5),
            )
            MissionRequirementFactory(mission=mission, skill=skill, min_proficiency=1)
            crew = UserFactory(role=Role.CREW_MEMBER, tenant=tenant)
            CrewSkillFactory(user=crew, skill=skill, proficiency=5)
            AssignmentFactory(mission=mission, user=crew, status=AssignmentStatus.ACCEPTED)

    def make_irrelevant(n):
        for _ in range(n):
            MissionFactory(tenant=tenant, created_by=lead, status=MissionStatus.COMPLETED)

    make_relevant(2)
    with django_assert_num_queries(1 + 3 * 2):
        staffing_readiness()

    # Adding irrelevant history must not change the count for the same relevant set.
    make_irrelevant(10)
    with django_assert_num_queries(1 + 3 * 2):
        staffing_readiness()

    # Adding more relevant missions scales the count by exactly 3 each.
    make_relevant(3)
    with django_assert_num_queries(1 + 3 * 5):
        staffing_readiness()


# --------------------------------------------------------------------- crew_utilization


def test_utilization_clips_to_window(tenant):
    crew = UserFactory(role=Role.CREW_MEMBER, tenant=tenant, name="Busy Bee")
    UserFactory(role=Role.CREW_MEMBER, tenant=tenant, name="Idle")
    mission = MissionFactory(
        tenant=tenant,
        status=MissionStatus.ACTIVE,
        start_date=TODAY,
        end_date=TODAY + dt.timedelta(days=200),
    )
    AssignmentFactory(mission=mission, user=crew, status=AssignmentStatus.ACCEPTED)
    data = crew_utilization(window_days=90)
    busy = next(c for c in data["crew"] if c["name"] == "Busy Bee")
    idle = next(c for c in data["crew"] if c["name"] == "Idle")
    assert busy["assigned_days"] == 90 and busy["utilization_pct"] == 100
    assert idle["assigned_days"] == 0
    assert data["org_utilization_pct"] == 50


def test_utilization_ignores_proposed_and_non_live_missions(tenant):
    accepted_crew = UserFactory(role=Role.CREW_MEMBER, tenant=tenant, name="Accepted")
    proposed_crew = UserFactory(role=Role.CREW_MEMBER, tenant=tenant, name="Proposed Only")
    draft_crew = UserFactory(role=Role.CREW_MEMBER, tenant=tenant, name="On Draft Mission")

    active_mission = MissionFactory(
        tenant=tenant,
        status=MissionStatus.ACTIVE,
        start_date=TODAY,
        end_date=TODAY + dt.timedelta(days=10),
    )
    AssignmentFactory(mission=active_mission, user=accepted_crew, status=AssignmentStatus.ACCEPTED)
    AssignmentFactory(mission=active_mission, user=proposed_crew, status=AssignmentStatus.PROPOSED)

    draft_mission = MissionFactory(
        tenant=tenant,
        status=MissionStatus.DRAFT,
        start_date=TODAY,
        end_date=TODAY + dt.timedelta(days=10),
    )
    AssignmentFactory(mission=draft_mission, user=draft_crew, status=AssignmentStatus.ACCEPTED)

    data = crew_utilization(window_days=10)
    by_name = {c["name"]: c for c in data["crew"]}
    assert by_name["Accepted"]["assigned_days"] == 10
    assert by_name["Proposed Only"]["assigned_days"] == 0
    assert by_name["On Draft Mission"]["assigned_days"] == 0


def test_utilization_query_count_is_constant(tenant, django_assert_num_queries):
    def make_crew_and_assignments(n):
        mission = MissionFactory(
            tenant=tenant,
            status=MissionStatus.ACTIVE,
            start_date=TODAY,
            end_date=TODAY + dt.timedelta(days=30),
        )
        for _ in range(n):
            crew = UserFactory(role=Role.CREW_MEMBER, tenant=tenant)
            AssignmentFactory(mission=mission, user=crew, status=AssignmentStatus.ACCEPTED)

    make_crew_and_assignments(2)
    with django_assert_num_queries(2):
        crew_utilization()

    make_crew_and_assignments(20)
    with django_assert_num_queries(2):
        crew_utilization()


# --------------------------------------------------------------------- skill_gaps


def test_skill_gap_flagged(tenant):
    lead = UserFactory(role=Role.MISSION_LEAD, tenant=tenant)
    mission = MissionFactory(
        tenant=tenant,
        created_by=lead,
        start_date=TODAY + dt.timedelta(days=5),
        end_date=TODAY + dt.timedelta(days=10),
    )
    scarce = SkillFactory(tenant=tenant, name="Xenobotany")
    MissionRequirementFactory(mission=mission, skill=scarce, min_proficiency=7, required_count=3)
    one_expert = UserFactory(role=Role.CREW_MEMBER, tenant=tenant)
    CrewSkillFactory(user=one_expert, skill=scarce, proficiency=9)
    gaps = skill_gaps()
    row = next(g for g in gaps if g["skill_name"] == "Xenobotany")
    assert row == {
        "skill_id": scarce.id,
        "skill_name": "Xenobotany",
        "open_seats": 3,
        "qualified_crew": 1,
        "gap": True,
    }


def test_skill_gap_no_gap_when_enough_qualified_crew(tenant):
    lead = UserFactory(role=Role.MISSION_LEAD, tenant=tenant)
    mission = MissionFactory(
        tenant=tenant,
        created_by=lead,
        start_date=TODAY + dt.timedelta(days=5),
        end_date=TODAY + dt.timedelta(days=10),
    )
    plenty = SkillFactory(tenant=tenant, name="Plumbing")
    MissionRequirementFactory(mission=mission, skill=plenty, min_proficiency=3, required_count=1)
    qualified = UserFactory(role=Role.CREW_MEMBER, tenant=tenant)
    CrewSkillFactory(user=qualified, skill=plenty, proficiency=6)
    unqualified = UserFactory(role=Role.CREW_MEMBER, tenant=tenant)
    CrewSkillFactory(user=unqualified, skill=plenty, proficiency=1)
    inactive_but_qualified = UserFactory(role=Role.CREW_MEMBER, tenant=tenant, is_active=False)
    CrewSkillFactory(user=inactive_but_qualified, skill=plenty, proficiency=9)

    row = next(g for g in skill_gaps() if g["skill_name"] == "Plumbing")
    assert row["qualified_crew"] == 1
    assert row["gap"] is False


def test_skill_gap_excludes_skills_from_closed_missions(tenant):
    lead = UserFactory(role=Role.MISSION_LEAD, tenant=tenant)
    completed = MissionFactory(
        tenant=tenant,
        created_by=lead,
        status=MissionStatus.COMPLETED,
        start_date=TODAY - dt.timedelta(days=20),
        end_date=TODAY - dt.timedelta(days=1),
    )
    irrelevant_skill = SkillFactory(tenant=tenant, name="Obsolete Tech")
    MissionRequirementFactory(mission=completed, skill=irrelevant_skill, required_count=5)
    assert skill_gaps() == []


def test_skill_gaps_query_count_is_constant(tenant, django_assert_num_queries):
    lead = UserFactory(role=Role.MISSION_LEAD, tenant=tenant)

    def make_skills_and_requirements(n):
        mission = MissionFactory(
            tenant=tenant,
            created_by=lead,
            status=MissionStatus.APPROVED,
            start_date=TODAY + dt.timedelta(days=5),
            end_date=TODAY + dt.timedelta(days=10),
        )
        for _ in range(n):
            skill = SkillFactory(tenant=tenant)
            MissionRequirementFactory(mission=mission, skill=skill, required_count=1)
            crew = UserFactory(role=Role.CREW_MEMBER, tenant=tenant)
            CrewSkillFactory(user=crew, skill=skill, proficiency=5)

    make_skills_and_requirements(2)
    with django_assert_num_queries(2):
        skill_gaps()

    make_skills_and_requirements(15)
    with django_assert_num_queries(2):
        skill_gaps()
