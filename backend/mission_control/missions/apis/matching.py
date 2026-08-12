"""Match API: expose Task 5.1's auto-matching engine over HTTP.

Read-only -- `match_mission` makes no assignments (see its docstring: it is pure), so
this endpoint calls it directly and serialises the result. No service, no write.
"""

import dataclasses

from rest_framework.response import Response
from rest_framework.views import APIView

from mission_control.common.exceptions import ApplicationError
from mission_control.missions.models import MissionStatus
from mission_control.missions.selectors import missions as mission_selectors
from mission_control.missions.services.matching import match_mission
from mission_control.users.permissions import Permission, ensure_permission

#: Mirrors `missions.services.assignments.TERMINAL` -- matching a mission that can no
#: longer be staffed is meaningless, same as proposing an assignment to one.
TERMINAL = frozenset({MissionStatus.COMPLETED, MissionStatus.CANCELLED})


class MissionMatchApi(APIView):
    def post(self, request, mission_id: int):
        ensure_permission(request.user, Permission.MATCH_RUN)
        mission = mission_selectors.mission_get(mission_id)
        if mission.status in TERMINAL:
            raise ApplicationError("Cannot match a completed or cancelled mission.")
        return Response(dataclasses.asdict(match_mission(mission)))
