from django.urls import path

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
]
