import dataclasses
import datetime as dt
import json

import pytest

from mission_control.missions.factories import (
    AssignmentFactory,
    MissionFactory,
    MissionRequirementFactory,
)
from mission_control.missions.models import AssignmentStatus, MissionStatus
from mission_control.missions.services.matching import (
    ALL_QUALIFIED_UNAVAILABLE,
    MAX_CREW_TOO_SMALL,
    NO_QUALIFIED_CREW,
    NOT_ENOUGH_QUALIFIED_CREW,
    W_PROFICIENCY,
    W_SOFT_CONFLICT,
    W_WORKLOAD,
    WORKLOAD_WINDOW_DAYS,
    match_mission,
)
from mission_control.tenants.context import set_current_tenant_id
from mission_control.users.factories import CrewSkillFactory, SkillFactory, UserFactory
from mission_control.users.roles import Role

pytestmark = pytest.mark.django_db
D = dt.date


@pytest.fixture
def mission():
    m = MissionFactory(start_date=D(2026, 9, 1), end_date=D(2026, 9, 10), min_crew=1, max_crew=4)
    set_current_tenant_id(m.tenant_id)
    return m


def crew_with(mission, skills: dict, name="Crew"):
    user = UserFactory(role=Role.CREW_MEMBER, tenant=mission.tenant, name=name)
    for skill, prof in skills.items():
        CrewSkillFactory(user=user, skill=skill, proficiency=prof)
    return user


def busy_on(mission, user, *, start, end, status=MissionStatus.ACTIVE, name="Other Op"):
    """Give `user` an accepted assignment on another mission of `status`."""
    other = MissionFactory(
        tenant=mission.tenant, status=status, start_date=start, end_date=end, name=name
    )
    AssignmentFactory(mission=other, user=user, status=AssignmentStatus.ACCEPTED)
    return other


# --------------------------------------------------------------- the brief's scenarios


def test_assembles_covering_team_with_explanations(mission):
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    nav = SkillFactory(tenant=mission.tenant, name="Navigation")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=6)
    MissionRequirementFactory(mission=mission, skill=nav, min_proficiency=5)
    pilot = crew_with(mission, {piloting: 8}, "Pilot Pat")
    navigator = crew_with(mission, {nav: 7}, "Nav Nia")
    result = match_mission(mission)
    assert {m.user_id for m in result.team} == {pilot.id, navigator.id}
    assert result.unfilled_seats == []
    pat = next(m for m in result.team if m.user_id == pilot.id)
    assert pat.seats[0]["skill_name"] == "Piloting"
    assert set(pat.breakdown) == {"proficiency_fit", "workload_balance", "soft_conflict_penalty"}


def test_generalist_preferred_over_specialists(mission):
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    nav = SkillFactory(tenant=mission.tenant, name="Navigation")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5)
    MissionRequirementFactory(mission=mission, skill=nav, min_proficiency=5)
    crew_with(mission, {piloting: 9}, "Specialist P")
    crew_with(mission, {nav: 9}, "Specialist N")
    generalist = crew_with(mission, {piloting: 6, nav: 6}, "Generalist G")
    result = match_mission(mission)
    assert result.team[0].user_id == generalist.id
    assert len(result.team[0].seats) == 2


def test_workload_balance_breaks_tie(mission):
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5)
    busy = crew_with(mission, {piloting: 7}, "Busy")
    fresh = crew_with(mission, {piloting: 7}, "Fresh")
    busy_on(mission, busy, start=D(2026, 8, 1), end=D(2026, 8, 30))
    result = match_mission(mission)
    assert result.team[0].user_id == fresh.id


def test_existing_accepted_crew_reduce_open_seats(mission):
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5, required_count=2)
    covered = crew_with(mission, {piloting: 8}, "Already In")
    AssignmentFactory(mission=mission, user=covered, status=AssignmentStatus.ACCEPTED)
    crew_with(mission, {piloting: 7}, "Candidate")
    result = match_mission(mission)
    assert len(result.team) == 1  # only one open seat left
    assert result.team[0].name == "Candidate"


def test_infeasible_diagnoses(mission):
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    welding = SkillFactory(tenant=mission.tenant, name="Welding")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=9)
    MissionRequirementFactory(mission=mission, skill=welding, min_proficiency=5)
    crew_with(mission, {piloting: 6}, "Underqualified")
    blocked = crew_with(mission, {welding: 8}, "Blocked")
    busy_on(mission, blocked, start=D(2026, 9, 5), end=D(2026, 9, 15))
    result = match_mission(mission)
    reasons = {u.skill_name: u.reason for u in result.unfilled_seats}
    assert reasons == {
        "Piloting": NO_QUALIFIED_CREW,
        "Welding": ALL_QUALIFIED_UNAVAILABLE,
    }


def test_top_up_to_min_crew(mission):
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5)
    mission.min_crew = 2
    mission.save()
    crew_with(mission, {piloting: 8}, "Pilot")
    crew_with(mission, {}, "Extra Hands")
    result = match_mission(mission)
    assert len(result.team) == 2


def test_alternatives_exclude_team(mission):
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5)
    for i, prof in enumerate((9, 8, 7, 6)):
        crew_with(mission, {piloting: prof}, f"P{i}")
    result = match_mission(mission)
    alt = result.alternatives[0]
    team_ids = {m.user_id for m in result.team}
    assert len(alt.candidates) == 3
    assert team_ids.isdisjoint({c["user_id"] for c in alt.candidates})


def test_deterministic(mission):
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5, required_count=2)
    for i in range(5):
        crew_with(mission, {piloting: 7}, f"Twin {i}")
    r1, r2 = match_mission(mission), match_mission(mission)
    assert dataclasses.asdict(r1) == dataclasses.asdict(r2)


# ------------------------------------------------------------------- scoring formula


def test_weights_are_the_specified_constants():
    assert (W_PROFICIENCY, W_WORKLOAD, W_SOFT_CONFLICT, WORKLOAD_WINDOW_DAYS) == (
        1.0,
        0.5,
        0.75,
        90,
    )


def test_score_is_the_documented_formula(mission):
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5)
    crew_with(mission, {piloting: 8}, "Pilot")
    member = match_mission(mission).team[0]
    # fit = (8 - 5) / 9 = 0.333; balance = 1 (no workload); penalty = 0
    assert member.breakdown == {
        "proficiency_fit": 0.333,
        "workload_balance": 1.0,
        "soft_conflict_penalty": 0.0,
    }
    assert member.workload_days == 0
    assert member.score == round(1.0 * (3 / 9) + 0.5 * 1.0, 3)


def test_soft_conflict_is_penalised_not_excluded(mission):
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5)
    conflicted = crew_with(mission, {piloting: 8}, "Conflicted")
    busy_on(
        mission,
        conflicted,
        start=D(2026, 9, 5),
        end=D(2026, 9, 15),
        status=MissionStatus.PENDING_APPROVAL,
        name="Maybe Op",
    )
    member = match_mission(mission).team[0]
    assert member.user_id == conflicted.id  # surfaced, not excluded
    assert member.breakdown["soft_conflict_penalty"] == 1.0
    assert member.score == round(1.0 * (3 / 9) + 0.5 * 1.0 - 0.75 * 1.0, 3)
    assert [c["mission_name"] for c in member.soft_conflicts] == ["Maybe Op"]


def test_hard_blocked_crew_never_enter_the_team(mission):
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5)
    blocked = crew_with(mission, {piloting: 10}, "Blocked Ace")
    busy_on(mission, blocked, start=D(2026, 9, 10), end=D(2026, 9, 20))
    weaker = crew_with(mission, {piloting: 5}, "Available")
    result = match_mission(mission)
    assert [m.user_id for m in result.team] == [weaker.id]
    assert blocked.id not in {c["user_id"] for c in result.alternatives[0].candidates}


def test_workload_counts_only_days_inside_the_window(mission):
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5)
    heavy = crew_with(mission, {piloting: 5}, "Heavy")
    # Starts long before the 90-day window opens and ends inside it; only the
    # in-window portion counts, and it never overlaps the mission itself.
    window_start = mission.start_date - dt.timedelta(days=WORKLOAD_WINDOW_DAYS)
    busy_on(mission, heavy, start=D(2026, 1, 5), end=D(2026, 8, 20))
    expected = (D(2026, 8, 20) - window_start).days + 1
    member = match_mission(mission).team[0]
    assert member.user_id == heavy.id
    assert member.workload_days == expected
    assert member.breakdown["workload_balance"] == round(1 - min(expected / 90, 1), 3)


def test_workload_ignores_commitments_outside_the_window(mission):
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5)
    far = crew_with(mission, {piloting: 5}, "Far Away")
    busy_on(mission, far, start=D(2027, 6, 1), end=D(2027, 6, 30))
    member = match_mission(mission).team[0]
    assert member.workload_days == 0
    assert member.breakdown["workload_balance"] == 1.0


def test_workload_ignores_unaccepted_and_unapproved_commitments(mission):
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5, required_count=2)
    proposed_elsewhere = crew_with(mission, {piloting: 5}, "Proposed Elsewhere")
    draft_elsewhere = crew_with(mission, {piloting: 5}, "Accepted On Draft")
    nearby = MissionFactory(
        tenant=mission.tenant,
        status=MissionStatus.ACTIVE,
        start_date=D(2026, 8, 1),
        end_date=D(2026, 8, 20),
    )
    AssignmentFactory(mission=nearby, user=proposed_elsewhere, status=AssignmentStatus.PROPOSED)
    busy_on(
        mission,
        draft_elsewhere,
        start=D(2026, 8, 1),
        end=D(2026, 8, 20),
        status=MissionStatus.DRAFT,
    )
    result = match_mission(mission)
    assert {m.workload_days for m in result.team} == {0}


# ------------------------------------------------------------------ seats & capacity


def test_one_seat_per_skill_and_the_most_demanding_one(mission):
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    easy = MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=4)
    hard = MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=8)
    ace = crew_with(mission, {piloting: 9}, "Ace")
    result = match_mission(mission)
    ace_member = next(m for m in result.team if m.user_id == ace.id)
    assert [s["requirement_id"] for s in ace_member.seats] == [hard.id]
    # Room to spare (open_capacity 3) and nobody blocked: the roster is just too thin,
    # which is NOT "max_crew too small" — that would contradict open_capacity.
    assert [(u.requirement_id, u.reason) for u in result.unfilled_seats] == [
        (easy.id, NOT_ENOUGH_QUALIFIED_CREW)
    ]
    assert result.open_capacity == 3


def test_capacity_is_limited_by_max_crew(mission):
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5, required_count=3)
    mission.max_crew = 2
    mission.save()
    for i in range(4):
        crew_with(mission, {piloting: 7}, f"P{i}")
    result = match_mission(mission)
    assert len(result.team) == 2
    assert result.open_capacity == 0
    assert [u.reason for u in result.unfilled_seats] == [MAX_CREW_TOO_SMALL]


def test_open_capacity_accounts_for_live_assignments(mission):
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5)
    sitting = crew_with(mission, {piloting: 5}, "Proposed Already")
    AssignmentFactory(mission=mission, user=sitting, status=AssignmentStatus.PROPOSED)
    crew_with(mission, {piloting: 6}, "Newcomer")
    result = match_mission(mission)
    # max_crew 4 - 1 live assignment = 3 capacity, one of which the newcomer takes.
    assert result.open_capacity == 2
    assert sitting.id not in {m.user_id for m in result.team}


@pytest.mark.parametrize("live_status", [AssignmentStatus.PROPOSED, AssignmentStatus.ACCEPTED])
def test_deactivated_live_member_frees_their_seat(mission, live_status):
    """A member deactivated after being staffed holds neither capacity nor a min_crew slot.

    Per the standing ruling, deactivated crew do not fill staffing seats. If their live
    assignment still consumed a max_crew seat, the matcher would under-propose and stop
    the top-up early, handing back a team the approve guard then rejects as short.
    """
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5)
    mission.min_crew = 2
    mission.save()
    ghost = crew_with(mission, {piloting: 9}, "Ghost")
    AssignmentFactory(mission=mission, user=ghost, status=live_status)
    ghost.is_active = False
    ghost.save()
    crew_with(mission, {piloting: 7}, "Pilot")
    crew_with(mission, {}, "Extra Hands")

    result = match_mission(mission)
    # The seat the ghost appeared to hold is open again, and the top-up runs to min_crew.
    assert [m.name for m in result.team] == ["Pilot", "Extra Hands"]
    assert ghost.id not in {m.user_id for m in result.team}
    assert result.unfilled_seats == []
    assert result.open_capacity == 2  # max_crew 4 - 2 proposed; the ghost costs nothing


def test_active_live_member_still_consumes_capacity(mission):
    """The control for the test above: an *active* live member does hold their seat."""
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5)
    mission.min_crew = 2
    mission.save()
    sitting = crew_with(mission, {piloting: 9}, "Sitting")
    AssignmentFactory(mission=mission, user=sitting, status=AssignmentStatus.PROPOSED)
    crew_with(mission, {piloting: 7}, "Pilot")
    crew_with(mission, {}, "Extra Hands")

    result = match_mission(mission)
    assert [m.name for m in result.team] == ["Pilot"]  # live 1 + team 1 already meets min_crew
    assert result.open_capacity == 2  # max_crew 4 - 1 live - 1 proposed


def test_thin_roster_is_not_reported_as_max_crew_too_small(mission):
    """Two seats, one qualified person, plenty of room: the roster is the constraint."""
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5, required_count=2)
    only = crew_with(mission, {piloting: 8}, "The Only One")

    result = match_mission(mission)
    assert [m.user_id for m in result.team] == [only.id]
    assert [u.reason for u in result.unfilled_seats] == [NOT_ENOUGH_QUALIFIED_CREW]
    assert result.open_capacity == 3  # not blocked, not full — just nobody else qualified


def test_diagnosis_reasons_are_a_closed_set_of_four():
    """Every reason the engine can emit, and the exact condition that produces it."""
    assert {
        NO_QUALIFIED_CREW,
        ALL_QUALIFIED_UNAVAILABLE,
        MAX_CREW_TOO_SMALL,
        NOT_ENOUGH_QUALIFIED_CREW,
    } == {
        "no qualified crew",
        "all qualified crew unavailable",
        "max_crew too small",
        "not enough qualified crew",
    }


def test_max_crew_too_small_is_only_reported_when_there_is_no_room(mission):
    """`max_crew too small` and a non-zero `open_capacity` must never co-occur."""
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5, required_count=6)
    for i in range(6):
        crew_with(mission, {piloting: 7}, f"P{i}")

    result = match_mission(mission)
    assert len(result.team) == 4  # max_crew
    assert result.open_capacity == 0
    assert [u.reason for u in result.unfilled_seats] == [MAX_CREW_TOO_SMALL] * 2


def test_mission_with_no_requirements_still_tops_up(mission):
    mission.min_crew = 2
    mission.save()
    crew_with(mission, {}, "Hand A")
    crew_with(mission, {}, "Hand B")
    crew_with(mission, {}, "Hand C")
    result = match_mission(mission)
    assert len(result.team) == 2
    assert all(m.seats == [] for m in result.team)
    assert result.unfilled_seats == []
    assert result.alternatives == []


def test_empty_roster_yields_an_empty_plan(mission):
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5)
    result = match_mission(mission)
    assert result.team == []
    assert [u.reason for u in result.unfilled_seats] == [NO_QUALIFIED_CREW]
    assert result.alternatives[0].candidates == []


def test_inactive_and_non_crew_are_never_matched(mission):
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5)
    retired = crew_with(mission, {piloting: 10}, "Retired")
    retired.is_active = False
    retired.save()
    lead = UserFactory(role=Role.MISSION_LEAD, tenant=mission.tenant, name="Lead")
    CrewSkillFactory(user=lead, skill=piloting, proficiency=10)
    result = match_mission(mission)
    assert result.team == []
    assert [u.reason for u in result.unfilled_seats] == [NO_QUALIFIED_CREW]


def test_other_tenants_crew_are_never_matched(mission):
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5)
    other_mission = MissionFactory(start_date=D(2026, 9, 1), end_date=D(2026, 9, 10))
    other_skill = SkillFactory(tenant=other_mission.tenant, name="Piloting")
    crew_with(other_mission, {other_skill: 10}, "Foreign Ace")
    result = match_mission(mission)
    assert result.team == []
    assert [u.reason for u in result.unfilled_seats] == [NO_QUALIFIED_CREW]


def test_unfilled_seat_is_reported_once_per_open_seat(mission):
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5, required_count=3)
    result = match_mission(mission)
    assert [u.reason for u in result.unfilled_seats] == [NO_QUALIFIED_CREW] * 3


# ---------------------------------------------------------------------- alternatives


def test_alternatives_are_ranked_by_score_descending(mission):
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5)
    people = [crew_with(mission, {piloting: prof}, f"P{prof}") for prof in (9, 8, 7, 6, 5)]
    result = match_mission(mission)
    alt = result.alternatives[0]
    assert [c["user_id"] for c in alt.candidates] == [p.id for p in people[1:4]]
    assert [c["proficiency"] for c in alt.candidates] == [8, 7, 6]
    # Exact scores, each computed for THIS requirement's seat: fit = (prof - 5) / 9,
    # balance 1, no penalty. Scoring the bench with no seat would make all three 0.5.
    assert [c["score"] for c in alt.candidates] == [
        round(3 / 9 + 0.5, 3),
        round(2 / 9 + 0.5, 3),
        round(1 / 9 + 0.5, 3),
    ]
    assert alt.candidates == sorted(alt.candidates, key=lambda c: -c["score"])
    assert (alt.skill_name, alt.min_proficiency) == ("Piloting", 5)


def test_bench_order_follows_score_not_user_id(mission):
    """Equal proficiency, unequal workload: the score must separate them.

    Deliberately shaped so an id tie-break cannot fake it — the worse candidate has the
    LOWER id, so ranking that fell through to `user_id` would invert this order.
    """
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5)
    crew_with(mission, {piloting: 9}, "Taken")  # wins the single open seat
    busy = crew_with(mission, {piloting: 7}, "Busy")
    fresh = crew_with(mission, {piloting: 7}, "Fresh")
    busy_on(mission, busy, start=D(2026, 7, 1), end=D(2026, 8, 9))  # 40 days in-window
    assert busy.id < fresh.id

    alt = match_mission(mission).alternatives[0]
    assert [c["name"] for c in alt.candidates] == ["Fresh", "Busy"]
    assert [c["proficiency"] for c in alt.candidates] == [7, 7]
    assert [c["score"] for c in alt.candidates] == [
        round(2 / 9 + 0.5 * 1.0, 3),
        round(2 / 9 + 0.5 * (1 - 40 / 90), 3),
    ]
    assert alt.candidates[0]["score"] > alt.candidates[1]["score"]


def test_alternatives_exclude_the_underqualified_and_the_hard_blocked(mission):
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=7)
    crew_with(mission, {piloting: 8}, "Taken")
    crew_with(mission, {piloting: 6}, "Underqualified")
    blocked = crew_with(mission, {piloting: 9}, "Blocked")
    busy_on(mission, blocked, start=D(2026, 9, 3), end=D(2026, 9, 4))
    result = match_mission(mission)
    assert result.alternatives[0].candidates == []


def test_alternatives_are_reported_for_covered_requirements_too(mission):
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5)
    covered = crew_with(mission, {piloting: 8}, "Already In")
    AssignmentFactory(mission=mission, user=covered, status=AssignmentStatus.ACCEPTED)
    spare = crew_with(mission, {piloting: 7}, "Spare")
    result = match_mission(mission)
    assert result.unfilled_seats == []
    assert [c["user_id"] for c in result.alternatives[0].candidates] == [spare.id]


# ------------------------------------------------------------ determinism & queries


def test_ties_break_on_ascending_user_id(mission):
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5, required_count=2)
    twins = [crew_with(mission, {piloting: 7}, f"Twin {i}") for i in range(4)]
    result = match_mission(mission)
    assert [m.user_id for m in result.team] == sorted(t.id for t in twins)[:2]
    assert [c["user_id"] for c in result.alternatives[0].candidates] == sorted(t.id for t in twins)[
        2:
    ]


def test_result_is_json_serializable(mission):
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5)
    conflicted = crew_with(mission, {piloting: 8}, "Conflicted")
    busy_on(
        mission,
        conflicted,
        start=D(2026, 9, 5),
        end=D(2026, 9, 15),
        status=MissionStatus.PENDING_APPROVAL,
    )
    crew_with(mission, {piloting: 6}, "Spare")
    payload = json.loads(json.dumps(dataclasses.asdict(match_mission(mission))))
    assert set(payload) == {"team", "unfilled_seats", "alternatives", "open_capacity"}
    assert set(payload["team"][0]) == {
        "user_id",
        "name",
        "seats",
        "score",
        "breakdown",
        "workload_days",
        "soft_conflicts",
    }


def _big_scenario(mission, crew_count, tag="A"):
    piloting = SkillFactory(tenant=mission.tenant, name=f"Piloting {tag}")
    nav = SkillFactory(tenant=mission.tenant, name=f"Navigation {tag}")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5, required_count=2)
    MissionRequirementFactory(mission=mission, skill=nav, min_proficiency=4)
    seated = crew_with(mission, {piloting: 9}, "Seated")
    AssignmentFactory(mission=mission, user=seated, status=AssignmentStatus.ACCEPTED)
    for i in range(crew_count):
        person = crew_with(mission, {piloting: 5 + (i % 5), nav: 4 + (i % 6)}, f"Crew {tag}{i}")
        if i % 3 == 0:
            busy_on(
                mission,
                person,
                start=D(2026, 8, 1),
                end=D(2026, 8, 20),
                name=f"Past Op {tag}{i}",
            )


def test_query_count_is_constant_in_roster_size(mission, django_assert_num_queries):
    _big_scenario(mission, 3)
    with django_assert_num_queries(9):
        match_mission(mission)

    other = MissionFactory(
        tenant=mission.tenant,
        start_date=D(2026, 9, 1),
        end_date=D(2026, 9, 10),
        min_crew=1,
        max_crew=4,
    )
    _big_scenario(other, 30, tag="B")
    with django_assert_num_queries(9):
        match_mission(other)


def test_identical_data_yields_identical_results_across_runs(mission):
    _big_scenario(mission, 12)
    runs = [dataclasses.asdict(match_mission(mission)) for _ in range(3)]
    assert runs[0] == runs[1] == runs[2]


# ---------------------------------------------------- matcher and propose agree on seats (I3)


def test_open_capacity_and_the_propose_guard_agree_about_deactivated_members(mission):
    """The `max_crew` invariant was expressed twice and drifted: the matcher filtered
    live assignments on `user__is_active=True` (per the ruling that deactivated crew do
    not fill seats), `assignments_propose`'s guard did not. With one deactivated live
    member the matcher reported a free seat and proposed a candidate, and the propose
    click was then rejected with "This would exceed max_crew" -- an unactionable
    suggestion, and an error naming the wrong cause. Both now read `live_seat_count`.
    """
    from mission_control.missions.selectors.staffing import live_seat_count
    from mission_control.missions.services.assignments import assignments_propose

    mission.max_crew = 3
    mission.save(update_fields=["max_crew"])
    skill = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=skill, min_proficiency=1, required_count=3)

    quit_crew = crew_with(mission, {skill: 5}, name="Departed")
    AssignmentFactory(mission=mission, user=quit_crew, status=AssignmentStatus.PROPOSED)
    quit_crew.is_active = False
    quit_crew.save(update_fields=["is_active"])

    candidates = [crew_with(mission, {skill: 5}, name=f"Candidate {i}") for i in range(3)]
    lead = mission.created_by

    # The deactivated member holds no seat, so all three are free.
    assert live_seat_count(mission) == 0

    result = match_mission(mission)
    assert len(result.team) == 3, "the matcher should fill all three free seats"
    assert result.open_capacity == 0  # consumed by the team it just proposed

    # And the matcher's suggestion is actionable: proposing exactly the team it returned
    # is accepted rather than bounced by the propose guard's own max_crew count.
    proposed = assignments_propose(
        actor=lead, mission=mission, user_ids=[m.user_id for m in result.team]
    )
    assert {a.user_id for a in proposed} == {c.id for c in candidates}
    assert live_seat_count(mission) == 3
