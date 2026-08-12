"""Match API: expose Task 5.1's auto-matching engine over HTTP.

Read-only -- the engine makes no assignments (see `match_mission`'s docstring: it is
pure). The endpoint still goes through `services.matching.mission_match`, because the
one rule guarding it ("not on a completed or cancelled mission") is a business rule,
and business rules are not decided in the API layer.
"""

from rest_framework.response import Response
from rest_framework.views import APIView

from mission_control.missions.selectors import missions as mission_selectors
from mission_control.missions.services.matching import MatchResult, mission_match
from mission_control.users.permissions import Permission, ensure_permission


def match_payload(result: MatchResult) -> dict:
    """The wire shape of a `MatchResult`, mirroring `assignments.staffing_payload`.

    Fields are enumerated by hand rather than `dataclasses.asdict`, so this function is
    the one place the API contract is written down: an internal-bookkeeping field added
    to `ProposedMember`/`UnfilledSeat`/`RequirementAlternatives`/`MatchResult` later
    does not silently reach the wire, and Task 5.3's zod schemas have something
    explicit to be checked against. `seats`, `breakdown`, `soft_conflicts` and
    `candidates` are already plain dicts built by the engine (not further dataclasses),
    so -- as `staffing_payload` does for its own `soft_conflicts` -- they pass through
    unchanged.
    """
    return {
        "team": [
            {
                "user_id": member.user_id,
                "name": member.name,
                "seats": member.seats,
                "score": member.score,
                "breakdown": member.breakdown,
                "workload_days": member.workload_days,
                "soft_conflicts": member.soft_conflicts,
            }
            for member in result.team
        ],
        "unfilled_seats": [
            {
                "requirement_id": seat.requirement_id,
                "skill_name": seat.skill_name,
                "min_proficiency": seat.min_proficiency,
                "reason": seat.reason,
            }
            for seat in result.unfilled_seats
        ],
        "alternatives": [
            {
                "requirement_id": alt.requirement_id,
                "skill_name": alt.skill_name,
                "min_proficiency": alt.min_proficiency,
                "candidates": alt.candidates,
            }
            for alt in result.alternatives
        ],
        "open_capacity": result.open_capacity,
    }


class MissionMatchApi(APIView):
    def post(self, request, mission_id: int):
        ensure_permission(request.user, Permission.MATCH_RUN)
        mission = mission_selectors.mission_get(mission_id)
        result = mission_match(actor=request.user, mission=mission)
        return Response(match_payload(result))
