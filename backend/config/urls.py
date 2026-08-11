from django.urls import include, path

urlpatterns = [path("api/v1/", include("mission_control.users.urls"))]
