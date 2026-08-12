from django.urls import path

from mission_control.missions.apis.assignments import (
    AssignmentRemoveApi,
    AssignmentRespondApi,
    MissionAssignmentsBulkApi,
    MissionStaffingApi,
    MyAssignmentsApi,
)
from mission_control.missions.apis.missions import (
    MissionDetailApi,
    MissionListCreateApi,
    MissionRequirementsApi,
    MissionTransitionApi,
)

urlpatterns = [
    path("missions/", MissionListCreateApi.as_view()),
    path("missions/<int:mission_id>/", MissionDetailApi.as_view()),
    path("missions/<int:mission_id>/requirements/", MissionRequirementsApi.as_view()),
    path("missions/<int:mission_id>/transitions/", MissionTransitionApi.as_view()),
    path("missions/<int:mission_id>/staffing/", MissionStaffingApi.as_view()),
    path("missions/<int:mission_id>/assignments/", MissionAssignmentsBulkApi.as_view()),
    path("assignments/<int:assignment_id>/remove/", AssignmentRemoveApi.as_view()),
    path("assignments/<int:assignment_id>/respond/", AssignmentRespondApi.as_view()),
    path("me/assignments/", MyAssignmentsApi.as_view()),
]
