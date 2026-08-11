# mission_control.users URL routes are added in a later task (this app's APIs,
# e.g. auth/token and /auth/me/, are not part of Task 1.3's scope). This file exists
# only so config/urls.py's `include("mission_control.users.urls")` — present since
# Task 1.1 — resolves, restoring `manage.py check` to green.
urlpatterns = []
