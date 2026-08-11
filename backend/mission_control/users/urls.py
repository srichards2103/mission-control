from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from mission_control.users.apis.auth import MeApi
from mission_control.users.apis.skills import SkillListCreateApi, SkillUpdateApi

urlpatterns = [
    path("auth/token/", TokenObtainPairView.as_view()),
    path("auth/token/refresh/", TokenRefreshView.as_view()),
    path("auth/me/", MeApi.as_view()),
    path("skills/", SkillListCreateApi.as_view()),
    path("skills/<int:skill_id>/", SkillUpdateApi.as_view()),
]
