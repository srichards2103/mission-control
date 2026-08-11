from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from mission_control.users.apis.auth import MeApi

urlpatterns = [
    path("auth/token/", TokenObtainPairView.as_view()),
    path("auth/token/refresh/", TokenRefreshView.as_view()),
    path("auth/me/", MeApi.as_view()),
]
