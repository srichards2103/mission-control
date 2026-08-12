import datetime as dt

import pytest

from mission_control.missions.factories import (
    AssignmentFactory,
    MissionFactory,
    MissionRequirementFactory,
)
from mission_control.missions.models import AssignmentStatus, MissionStatus
from mission_control.missions.selectors.staffing import (
    HARD_BLOCK_MISSION_STATUSES,
    committed_assignments,
    hard_blocked_user_ids,
    mission_coverage,
    soft_conflicts_for_users,
    staffing_validation_errors,
)
from mission_control.tenants.context import set_current_tenant_id
from mission_control.users.factories import CrewSkillFactory, SkillFactory, UserFactory
from mission_control.users.roles import Role

pytestmark = pytest.mark.django_db

D = dt.date


@pytest.fixture
def tenant_ctx():
    mission = MissionFactory(start_date=D(2026, 9, 1), end_date=D(2026, 9, 10))
    set_current_tenant_id(mission.tenant_id)
    return mission


def crew_with(mission, skill, proficiency, name="Crew"):
    user = UserFactory(role=Role.CREW_MEMBER, tenant=mission.tenant, name=name)
    CrewSkillFactory(user=user, skill=skill, proficiency=proficiency)
    return user


def other_mission(mission, *, status, start, end, name="Other Op"):
    return MissionFactory(
        tenant=mission.tenant, status=status, start_date=start, end_date=end, name=name
    )


# --------------------------------------------------------------------------- hard block


def test_hard_block_only_from_accepted_on_approved_or_active(tenant_ctx):
    mission = tenant_ctx
    blocker = MissionFactory(
        tenant=mission.tenant,
        status=MissionStatus.APPROVED,
        start_date=D(2026, 9, 5),
        end_date=D(2026, 9, 15),
    )
    soft_m = MissionFactory(
        tenant=mission.tenant,
        status=MissionStatus.PENDING_APPROVAL,
        start_date=D(2026, 9, 5),
        end_date=D(2026, 9, 15),
    )
    hard_user = AssignmentFactory(mission=blocker, status=AssignmentStatus.ACCEPTED).user
    proposed_user = AssignmentFactory(mission=blocker, status=AssignmentStatus.PROPOSED).user
    soft_user = AssignmentFactory(mission=soft_m, status=AssignmentStatus.ACCEPTED).user

    blocked = hard_blocked_user_ids(start_date=mission.start_date, end_date=mission.end_date)
    assert hard_user.id in blocked
    assert proposed_user.id not in blocked and soft_user.id not in blocked


def test_no_block_when_dates_do_not_overlap(tenant_ctx):
    mission = tenant_ctx
    blocker = MissionFactory(
        tenant=mission.tenant,
        status=MissionStatus.ACTIVE,
        start_date=D(2026, 9, 11),
        end_date=D(2026, 9, 20),
    )
    user = AssignmentFactory(mission=blocker, status=AssignmentStatus.ACCEPTED).user
    assert user.id not in hard_blocked_user_ids(
        start_date=mission.start_date, end_date=mission.end_date
    )


@pytest.mark.parametrize("mission_status", list(MissionStatus))
@pytest.mark.parametrize("assignment_status", list(AssignmentStatus))
def test_status_axis_crossed_with_overlapping_dates(tenant_ctx, mission_status, assignment_status):
    """Same overlapping dates for every (assignment status x mission status) pair.

    Hard block iff accepted AND approved/active. Everything else that overlaps and is
    still live is a soft conflict; dead assignments are neither.
    """
    mission = tenant_ctx
    other = other_mission(
        mission, status=mission_status, start=D(2026, 9, 5), end=D(2026, 9, 15), name="Overlapper"
    )
    a = AssignmentFactory(mission=other, status=assignment_status)

    # Literal, NOT HARD_BLOCK_MISSION_STATUSES: deriving the expectation from the
    # production constant would keep all 28 cells green if the constant were widened.
    should_hard_block = assignment_status == AssignmentStatus.ACCEPTED and mission_status in {
        MissionStatus.APPROVED,
        MissionStatus.ACTIVE,
    }
    blocked = hard_blocked_user_ids(
        start_date=mission.start_date, end_date=mission.end_date, exclude_mission_id=mission.id
    )
    assert (a.user_id in blocked) is should_hard_block

    conflicts = soft_conflicts_for_users(
        user_ids=[a.user_id],
        start_date=mission.start_date,
        end_date=mission.end_date,
        exclude_mission_id=mission.id,
    )
    is_live = assignment_status in (AssignmentStatus.PROPOSED, AssignmentStatus.ACCEPTED)
    is_relevant_mission = mission_status not in (
        MissionStatus.COMPLETED,
        MissionStatus.CANCELLED,
    )
    should_soft_conflict = is_live and is_relevant_mission and not should_hard_block
    assert (a.user_id in conflicts) is should_soft_conflict


# ---------------------------------------------------------------------- date boundaries

# Mission under test runs 2026-09-01 .. 2026-09-10 (inclusive, day granularity).
OVERLAP_CASES = [
    ("identical", D(2026, 9, 1), D(2026, 9, 10), True),
    ("strictly inside", D(2026, 9, 3), D(2026, 9, 4), True),
    ("strictly outside (encloses)", D(2026, 8, 1), D(2026, 10, 1), True),
    ("partial overlap at start", D(2026, 8, 25), D(2026, 9, 1), True),
    ("partial overlap at end", D(2026, 9, 10), D(2026, 9, 20), True),
    ("touching before (ends on our start)", D(2026, 8, 20), D(2026, 9, 1), True),
    ("touching after (starts on our end)", D(2026, 9, 10), D(2026, 9, 30), True),
    ("one-day gap before", D(2026, 8, 20), D(2026, 8, 31), False),
    ("one-day gap after", D(2026, 9, 11), D(2026, 9, 30), False),
    ("single day inside", D(2026, 9, 5), D(2026, 9, 5), True),
    ("single day on first day", D(2026, 9, 1), D(2026, 9, 1), True),
    ("single day on last day", D(2026, 9, 10), D(2026, 9, 10), True),
    ("single day one before", D(2026, 8, 31), D(2026, 8, 31), False),
    ("single day one after", D(2026, 9, 11), D(2026, 9, 11), False),
]


@pytest.mark.parametrize(
    ("label", "start", "end", "overlaps"),
    OVERLAP_CASES,
    ids=[c[0] for c in OVERLAP_CASES],
)
def test_overlap_boundaries_for_hard_block(tenant_ctx, label, start, end, overlaps):
    mission = tenant_ctx
    blocker = other_mission(mission, status=MissionStatus.APPROVED, start=start, end=end)
    user = AssignmentFactory(mission=blocker, status=AssignmentStatus.ACCEPTED).user
    blocked = hard_blocked_user_ids(start_date=mission.start_date, end_date=mission.end_date)
    assert (user.id in blocked) is overlaps


@pytest.mark.parametrize(
    ("label", "start", "end", "overlaps"),
    OVERLAP_CASES,
    ids=[c[0] for c in OVERLAP_CASES],
)
def test_overlap_boundaries_for_soft_conflicts(tenant_ctx, label, start, end, overlaps):
    mission = tenant_ctx
    other = other_mission(mission, status=MissionStatus.DRAFT, start=start, end=end)
    a = AssignmentFactory(mission=other, status=AssignmentStatus.ACCEPTED)
    conflicts = soft_conflicts_for_users(
        user_ids=[a.user_id],
        start_date=mission.start_date,
        end_date=mission.end_date,
        exclude_mission_id=mission.id,
    )
    assert (a.user_id in conflicts) is overlaps


def test_single_day_mission_under_test_touching_both_sides(tenant_ctx):
    mission = tenant_ctx  # probe range is a single day
    day = D(2026, 9, 5)
    before = other_mission(mission, status=MissionStatus.ACTIVE, start=D(2026, 9, 1), end=day)
    after = other_mission(mission, status=MissionStatus.ACTIVE, start=day, end=D(2026, 9, 9))
    gap = other_mission(
        mission, status=MissionStatus.ACTIVE, start=D(2026, 9, 6), end=D(2026, 9, 9)
    )
    u_before = AssignmentFactory(mission=before, status=AssignmentStatus.ACCEPTED).user
    u_after = AssignmentFactory(mission=after, status=AssignmentStatus.ACCEPTED).user
    u_gap = AssignmentFactory(mission=gap, status=AssignmentStatus.ACCEPTED).user

    blocked = hard_blocked_user_ids(start_date=day, end_date=day)
    assert u_before.id in blocked
    assert u_after.id in blocked
    assert u_gap.id not in blocked


def test_hard_block_excludes_the_mission_being_staffed(tenant_ctx):
    mission = tenant_ctx
    mission.status = MissionStatus.APPROVED
    mission.save()
    a = AssignmentFactory(mission=mission, status=AssignmentStatus.ACCEPTED)
    args = {"start_date": mission.start_date, "end_date": mission.end_date}
    assert a.user_id in hard_blocked_user_ids(**args)
    assert a.user_id not in hard_blocked_user_ids(**args, exclude_mission_id=mission.id)


def test_hard_block_is_tenant_scoped(tenant_ctx):
    mission = tenant_ctx
    stranger_mission = MissionFactory(
        status=MissionStatus.ACTIVE, start_date=mission.start_date, end_date=mission.end_date
    )  # its own brand-new tenant
    stranger = AssignmentFactory(mission=stranger_mission, status=AssignmentStatus.ACCEPTED)
    assert stranger.user_id not in hard_blocked_user_ids(
        start_date=mission.start_date, end_date=mission.end_date
    )


# ------------------------------------------------------------------------ soft conflicts


def test_soft_conflicts_reported(tenant_ctx):
    mission = tenant_ctx
    other = MissionFactory(
        tenant=mission.tenant,
        status=MissionStatus.DRAFT,
        start_date=D(2026, 9, 5),
        end_date=D(2026, 9, 15),
        name="Draft Op",
    )
    a = AssignmentFactory(mission=other, status=AssignmentStatus.ACCEPTED)
    conflicts = soft_conflicts_for_users(
        user_ids=[a.user_id],
        start_date=mission.start_date,
        end_date=mission.end_date,
        exclude_mission_id=mission.id,
    )
    assert conflicts[a.user_id][0]["mission_name"] == "Draft Op"


def test_soft_conflict_entry_shape(tenant_ctx):
    mission = tenant_ctx
    other = other_mission(
        mission,
        status=MissionStatus.PENDING_APPROVAL,
        start=D(2026, 9, 2),
        end=D(2026, 9, 3),
        name="Pending Op",
    )
    a = AssignmentFactory(mission=other, status=AssignmentStatus.PROPOSED)
    entry = soft_conflicts_for_users(
        user_ids=[a.user_id],
        start_date=mission.start_date,
        end_date=mission.end_date,
        exclude_mission_id=mission.id,
    )[a.user_id][0]
    assert entry == {
        "mission_id": other.id,
        "mission_name": "Pending Op",
        "mission_status": MissionStatus.PENDING_APPROVAL,
        "assignment_status": AssignmentStatus.PROPOSED,
    }


def test_hard_blocked_assignment_is_not_also_a_soft_conflict(tenant_ctx):
    mission = tenant_ctx
    blocker = other_mission(
        mission, status=MissionStatus.ACTIVE, start=D(2026, 9, 5), end=D(2026, 9, 15)
    )
    a = AssignmentFactory(mission=blocker, status=AssignmentStatus.ACCEPTED)
    conflicts = soft_conflicts_for_users(
        user_ids=[a.user_id],
        start_date=mission.start_date,
        end_date=mission.end_date,
        exclude_mission_id=mission.id,
    )
    assert conflicts == {}


def test_soft_conflicts_only_for_requested_users_and_never_the_same_mission(tenant_ctx):
    mission = tenant_ctx
    a_here = AssignmentFactory(mission=mission, status=AssignmentStatus.PROPOSED)
    other = other_mission(
        mission, status=MissionStatus.DRAFT, start=D(2026, 9, 1), end=D(2026, 9, 2)
    )
    a_there = AssignmentFactory(mission=other, status=AssignmentStatus.PROPOSED)
    conflicts = soft_conflicts_for_users(
        user_ids=[a_here.user_id],
        start_date=mission.start_date,
        end_date=mission.end_date,
        exclude_mission_id=mission.id,
    )
    assert conflicts == {}
    assert a_there.user_id not in conflicts


def test_soft_conflicts_empty_user_list(tenant_ctx):
    mission = tenant_ctx
    assert (
        soft_conflicts_for_users(
            user_ids=[],
            start_date=mission.start_date,
            end_date=mission.end_date,
            exclude_mission_id=mission.id,
        )
        == {}
    )


def test_soft_conflicts_is_one_query_for_many_users(tenant_ctx, django_assert_num_queries):
    mission = tenant_ctx
    users = []
    for i in range(5):
        other = other_mission(
            mission,
            status=MissionStatus.DRAFT,
            start=D(2026, 9, 2),
            end=D(2026, 9, 3),
            name=f"D{i}",
        )
        users.append(AssignmentFactory(mission=other, status=AssignmentStatus.PROPOSED).user_id)
    with django_assert_num_queries(1):
        conflicts = soft_conflicts_for_users(
            user_ids=users,
            start_date=mission.start_date,
            end_date=mission.end_date,
            exclude_mission_id=mission.id,
        )
        for entries in conflicts.values():
            for entry in entries:
                entry["mission_name"]  # names come from the join, not lazy loads
    assert len(conflicts) == 5


# ----------------------------------------------------------------------------- coverage


def test_coverage_multi_row_same_skill(tenant_ctx):
    mission = tenant_ctx
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=9, required_count=1)
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5, required_count=2)
    for prof in (9, 6, 5):
        user = crew_with(mission, piloting, prof)
        AssignmentFactory(mission=mission, user=user, status=AssignmentStatus.ACCEPTED)
    report = mission_coverage(mission)
    assert report.fully_covered
    seat9 = next(r for r in report.requirements if r.min_proficiency == 9)
    assert [f["proficiency"] for f in seat9.filled_by] == [9]


def test_generalist_covers_two_skills_but_one_seat_per_skill(tenant_ctx):
    mission = tenant_ctx
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    nav = SkillFactory(tenant=mission.tenant, name="Navigation")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5, required_count=1)
    MissionRequirementFactory(mission=mission, skill=nav, min_proficiency=5, required_count=1)
    generalist = crew_with(mission, piloting, 8)
    CrewSkillFactory(user=generalist, skill=nav, proficiency=7)
    AssignmentFactory(mission=mission, user=generalist, status=AssignmentStatus.ACCEPTED)
    report = mission_coverage(mission)
    assert report.fully_covered  # one person, two different-skill seats


def test_one_member_cannot_fill_two_seats_of_the_same_skill(tenant_ctx):
    mission = tenant_ctx
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5, required_count=2)
    solo = crew_with(mission, piloting, 10)
    AssignmentFactory(mission=mission, user=solo, status=AssignmentStatus.ACCEPTED)
    report = mission_coverage(mission)
    row = report.requirements[0]
    assert row.filled_count == 1 and row.required_count == 2
    assert not report.fully_covered


def test_proposed_assignments_do_not_count(tenant_ctx):
    mission = tenant_ctx
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5, required_count=1)
    user = crew_with(mission, piloting, 8)
    AssignmentFactory(mission=mission, user=user, status=AssignmentStatus.PROPOSED)
    report = mission_coverage(mission)
    assert not report.fully_covered


def test_below_min_proficiency_does_not_fill_a_seat(tenant_ctx):
    mission = tenant_ctx
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=7, required_count=1)
    weak = crew_with(mission, piloting, 6)
    AssignmentFactory(mission=mission, user=weak, status=AssignmentStatus.ACCEPTED)
    report = mission_coverage(mission)
    assert report.accepted_count == 1
    assert report.requirements[0].filled_count == 0
    assert report.requirements[0].filled_by == []
    assert not report.fully_covered


def test_member_without_the_skill_does_not_fill_a_seat(tenant_ctx):
    mission = tenant_ctx
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    other_skill = SkillFactory(tenant=mission.tenant, name="Cooking")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=1, required_count=1)
    cook = crew_with(mission, other_skill, 10)
    AssignmentFactory(mission=mission, user=cook, status=AssignmentStatus.ACCEPTED)
    report = mission_coverage(mission)
    assert report.requirements[0].filled_count == 0
    assert not report.fully_covered


def test_greedy_does_not_waste_the_only_expert_on_a_low_seat(tenant_ctx):
    """Rows are served most-demanding-first, so the 9 lands on the ≥9 seat, not the ≥5 seat."""
    mission = tenant_ctx
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5, required_count=1)
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=9, required_count=1)
    for prof, name in ((5, "Novice"), (9, "Expert")):
        user = crew_with(mission, piloting, prof, name=name)
        AssignmentFactory(mission=mission, user=user, status=AssignmentStatus.ACCEPTED)
    report = mission_coverage(mission)
    assert report.fully_covered
    by_min = {r.min_proficiency: r for r in report.requirements}
    assert [f["name"] for f in by_min[9].filled_by] == ["Expert"]
    assert [f["name"] for f in by_min[5].filled_by] == ["Novice"]


def test_coverage_reports_filled_by_shape_and_counts(tenant_ctx):
    mission = tenant_ctx
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    req = MissionRequirementFactory(
        mission=mission, skill=piloting, min_proficiency=5, required_count=2
    )
    ada = crew_with(mission, piloting, 8, name="Ada Lovelace")
    AssignmentFactory(mission=mission, user=ada, status=AssignmentStatus.ACCEPTED)
    report = mission_coverage(mission)
    row = report.requirements[0]
    assert (row.requirement_id, row.skill_id, row.skill_name) == (req.id, piloting.id, "Piloting")
    assert row.filled_by == [{"user_id": ada.id, "name": "Ada Lovelace", "proficiency": 8}]


def test_mission_with_no_requirements_is_fully_covered(tenant_ctx):
    report = mission_coverage(tenant_ctx)
    assert report.requirements == [] and report.fully_covered and report.accepted_count == 0


def test_coverage_query_count_is_constant(tenant_ctx, django_assert_num_queries):
    mission = tenant_ctx
    skills = [SkillFactory(tenant=mission.tenant, name=f"Skill {i}") for i in range(3)]
    for skill in skills:
        MissionRequirementFactory(
            mission=mission, skill=skill, min_proficiency=3, required_count=2
        )
        MissionRequirementFactory(
            mission=mission, skill=skill, min_proficiency=8, required_count=1
        )
    for i in range(6):
        user = crew_with(mission, skills[i % 3], 9, name=f"Crew {i}")
        CrewSkillFactory(user=user, skill=skills[(i + 1) % 3], proficiency=4)
        AssignmentFactory(mission=mission, user=user, status=AssignmentStatus.ACCEPTED)
    with django_assert_num_queries(3):
        report = mission_coverage(mission)
        for row in report.requirements:
            row.skill_name, [f["name"] for f in row.filled_by]
    assert report.accepted_count == 6


# --------------------------------------------------------------------- validation errors


def test_validation_errors_list_problems(tenant_ctx):
    mission = tenant_ctx  # min_crew=1, no requirements covered yet
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=7, required_count=2)
    errors = staffing_validation_errors(mission)
    assert any("Piloting" in e for e in errors)
    assert any("min_crew" in e or "at least" in e for e in errors)


def test_validation_error_wording_for_partially_covered_requirement(tenant_ctx):
    mission = tenant_ctx
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=7, required_count=2)
    user = crew_with(mission, piloting, 8)
    AssignmentFactory(mission=mission, user=user, status=AssignmentStatus.ACCEPTED)
    errors = staffing_validation_errors(mission)
    assert any(e.startswith("Requirement Piloting ≥7 needs 2, has 1") for e in errors)


def test_validation_errors_flags_too_many_accepted(tenant_ctx):
    mission = tenant_ctx
    mission.min_crew, mission.max_crew = 1, 2
    mission.save()
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=1, required_count=1)
    for i in range(3):
        user = crew_with(mission, piloting, 5, name=f"Crew {i}")
        AssignmentFactory(mission=mission, user=user, status=AssignmentStatus.ACCEPTED)
    errors = staffing_validation_errors(mission)
    assert any("max_crew" in e for e in errors)
    assert not any("Requirement" in e for e in errors)


def test_validation_errors_name_hard_blocked_members(tenant_ctx):
    mission = tenant_ctx
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=1, required_count=1)
    ada = crew_with(mission, piloting, 9, name="Ada Lovelace")
    AssignmentFactory(mission=mission, user=ada, status=AssignmentStatus.ACCEPTED)
    elsewhere = other_mission(
        mission,
        status=MissionStatus.APPROVED,
        start=D(2026, 9, 10),
        end=D(2026, 9, 20),
        name="Ganymede Survey",
    )
    AssignmentFactory(mission=elsewhere, user=ada, status=AssignmentStatus.ACCEPTED)
    errors = staffing_validation_errors(mission)
    assert "Ada Lovelace is committed to 'Ganymede Survey'." in errors


def test_validation_errors_ignore_soft_conflicts_elsewhere(tenant_ctx):
    mission = tenant_ctx
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=1, required_count=1)
    ada = crew_with(mission, piloting, 9, name="Ada Lovelace")
    AssignmentFactory(mission=mission, user=ada, status=AssignmentStatus.ACCEPTED)
    draft = other_mission(
        mission,
        status=MissionStatus.DRAFT,
        start=D(2026, 9, 5),
        end=D(2026, 9, 20),
        name="Maybe Op",
    )
    AssignmentFactory(mission=draft, user=ada, status=AssignmentStatus.ACCEPTED)
    assert staffing_validation_errors(mission) == []


def test_validation_errors_hard_block_lookup_is_not_per_member(
    tenant_ctx, django_assert_num_queries
):
    mission = tenant_ctx
    mission.max_crew = 5
    mission.save()
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=1, required_count=4)
    elsewhere = other_mission(
        mission,
        status=MissionStatus.ACTIVE,
        start=D(2026, 9, 8),
        end=D(2026, 9, 20),
        name="Busy Op",
    )
    for i in range(4):
        user = crew_with(mission, piloting, 5, name=f"Crew {i}")
        AssignmentFactory(mission=mission, user=user, status=AssignmentStatus.ACCEPTED)
        AssignmentFactory(mission=elsewhere, user=user, status=AssignmentStatus.ACCEPTED)
    with django_assert_num_queries(4):  # 3 for coverage + 1 for the hard-block join
        errors = staffing_validation_errors(mission)
    assert len([e for e in errors if "committed to 'Busy Op'" in e]) == 4


# ------------------------------------------------------------------------- deactivation


def test_hard_block_constant_is_exactly_approved_and_active():
    """Pinned separately so the cross-product test can assert against a literal."""
    assert HARD_BLOCK_MISSION_STATUSES == frozenset(
        {MissionStatus.APPROVED, MissionStatus.ACTIVE}
    )


def test_deactivated_member_stops_filling_a_seat(tenant_ctx):
    mission = tenant_ctx
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5, required_count=1)
    ada = crew_with(mission, piloting, 9, name="Ada Lovelace")
    AssignmentFactory(mission=mission, user=ada, status=AssignmentStatus.ACCEPTED)
    assert mission_coverage(mission).fully_covered

    ada.is_active = False  # deactivated long after accepting
    ada.save()

    report = mission_coverage(mission)
    assert report.accepted_count == 0
    assert report.requirements[0].filled_count == 0
    assert report.requirements[0].filled_by == []
    assert not report.fully_covered


def test_deactivated_member_produces_validation_errors(tenant_ctx):
    mission = tenant_ctx  # min_crew=1
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5, required_count=1)
    ada = crew_with(mission, piloting, 9, name="Ada Lovelace")
    AssignmentFactory(mission=mission, user=ada, status=AssignmentStatus.ACCEPTED)
    assert staffing_validation_errors(mission) == []

    ada.is_active = False
    ada.save()

    errors = staffing_validation_errors(mission)
    assert any(e.startswith("Requirement Piloting ≥5 needs 1, has 0") for e in errors)
    assert any("min_crew" in e for e in errors)


def test_deactivated_member_is_not_reported_as_committed_elsewhere(tenant_ctx):
    """Coverage and the hard-block error agree: a deactivated member is simply not there."""
    mission = tenant_ctx
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=1, required_count=1)
    ada = crew_with(mission, piloting, 9, name="Ada Lovelace")
    AssignmentFactory(mission=mission, user=ada, status=AssignmentStatus.ACCEPTED)
    elsewhere = other_mission(
        mission,
        status=MissionStatus.APPROVED,
        start=D(2026, 9, 10),
        end=D(2026, 9, 20),
        name="Ganymede Survey",
    )
    AssignmentFactory(mission=elsewhere, user=ada, status=AssignmentStatus.ACCEPTED)
    assert any("committed to" in e for e in staffing_validation_errors(mission))

    ada.is_active = False
    ada.save()

    assert not any("committed to" in e for e in staffing_validation_errors(mission))


def test_active_members_still_fill_seats_when_a_colleague_is_deactivated(tenant_ctx):
    mission = tenant_ctx
    mission.max_crew = 3
    mission.save()
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5, required_count=1)
    gone = crew_with(mission, piloting, 10, name="Gone")
    stays = crew_with(mission, piloting, 6, name="Stays")
    for user in (gone, stays):
        AssignmentFactory(mission=mission, user=user, status=AssignmentStatus.ACCEPTED)
    gone.is_active = False
    gone.save()

    report = mission_coverage(mission)
    assert report.accepted_count == 1
    assert [f["name"] for f in report.requirements[0].filled_by] == ["Stays"]
    assert report.fully_covered
    assert staffing_validation_errors(mission) == []


def test_deactivation_does_not_change_the_hard_block_predicate(tenant_ctx):
    """Availability is stated purely in terms of statuses and dates — leave it alone."""
    mission = tenant_ctx
    blocker = other_mission(
        mission, status=MissionStatus.ACTIVE, start=D(2026, 9, 5), end=D(2026, 9, 15)
    )
    a = AssignmentFactory(mission=blocker, status=AssignmentStatus.ACCEPTED)
    a.user.is_active = False
    a.user.save()
    assert a.user_id in hard_blocked_user_ids(
        start_date=mission.start_date, end_date=mission.end_date
    )


# --------------------------------------------------------------- committed assignments


def test_committed_assignments_returns_the_hard_blocking_rows_themselves(tenant_ctx):
    """Same predicate as `hard_blocked_user_ids`, but with the missions attached."""
    mission = tenant_ctx
    committed = UserFactory(role=Role.CREW_MEMBER, tenant=mission.tenant, name="Committed")
    soft = UserFactory(role=Role.CREW_MEMBER, tenant=mission.tenant, name="Soft")
    hard = other_mission(
        mission, status=MissionStatus.ACTIVE, start=D(2026, 9, 5), end=D(2026, 9, 15)
    )
    AssignmentFactory(mission=hard, user=committed, status=AssignmentStatus.ACCEPTED)
    maybe = other_mission(
        mission,
        status=MissionStatus.PENDING_APPROVAL,
        start=D(2026, 9, 5),
        end=D(2026, 9, 15),
        name="Maybe Op",
    )
    AssignmentFactory(mission=maybe, user=soft, status=AssignmentStatus.ACCEPTED)

    rows = committed_assignments(
        user_ids=[committed.id, soft.id], start_date=D(2026, 9, 1), end_date=D(2026, 9, 10)
    )
    assert [(a.user_id, a.mission.name) for a in rows] == [(committed.id, hard.name)]
    assert {a.user_id for a in rows} == hard_blocked_user_ids(
        start_date=D(2026, 9, 1), end_date=D(2026, 9, 10)
    )


def test_committed_assignments_honours_the_window_and_the_exclusion(tenant_ctx):
    mission = tenant_ctx
    member = UserFactory(role=Role.CREW_MEMBER, tenant=mission.tenant, name="Member")
    AssignmentFactory(mission=mission, user=member, status=AssignmentStatus.ACCEPTED)
    mission.status = MissionStatus.APPROVED
    mission.save()
    far = other_mission(
        mission, status=MissionStatus.ACTIVE, start=D(2026, 12, 1), end=D(2026, 12, 5)
    )
    AssignmentFactory(mission=far, user=member, status=AssignmentStatus.ACCEPTED)

    same_range = committed_assignments(
        user_ids=[member.id],
        start_date=mission.start_date,
        end_date=mission.end_date,
        exclude_mission_id=mission.id,
    )
    assert list(same_range) == []  # own mission excluded, December is out of range

    wide = committed_assignments(
        user_ids=[member.id],
        start_date=mission.start_date,
        end_date=D(2026, 12, 31),
        exclude_mission_id=mission.id,
    )
    assert [a.mission_id for a in wide] == [far.id]


def test_committed_assignments_is_one_query(tenant_ctx, django_assert_num_queries):
    mission = tenant_ctx
    members = [
        UserFactory(role=Role.CREW_MEMBER, tenant=mission.tenant, name=f"M{i}") for i in range(6)
    ]
    for i, member in enumerate(members):
        op = other_mission(
            mission,
            status=MissionStatus.ACTIVE,
            start=D(2026, 9, 2),
            end=D(2026, 9, 8),
            name=f"Op {i}",
        )
        AssignmentFactory(mission=op, user=member, status=AssignmentStatus.ACCEPTED)

    with django_assert_num_queries(1):
        rows = committed_assignments(
            user_ids=[m.id for m in members], start_date=D(2026, 9, 1), end_date=D(2026, 9, 10)
        )
        # `select_related` means touching each mission adds no query.
        assert {a.mission.name for a in rows} == {f"Op {i}" for i in range(6)}
