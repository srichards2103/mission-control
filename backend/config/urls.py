from django.http import JsonResponse
from django.urls import include, path

urlpatterns = [
    path("api/v1/", include("mission_control.users.urls")),
    path("api/v1/", include("mission_control.missions.urls")),
]


# Django's own error pages, not DRF's, answer anything that never reaches a view: a URL
# that matches no pattern, and any exception the DRF handler declines (
# `common.exception_handler` returns None for a non-DRF, non-ApplicationError
# exception, which re-raises it into Django). Both used to render HTML, so the
# {"message", "extra"} envelope -- which the frontend's `errorMessage()` parses on
# every failure -- had two holes in it, both reachable in production (DEBUG=False).
#
# Signatures are Django's: `handler404(request, exception, template_name=...)` and
# `handler500(request, template_name=...)`. The keyword arguments are accepted and
# ignored -- there are no templates in this project (TEMPLATES = []), which is itself
# why the default handlers could not have rendered anything useful.


def handler404(request, exception=None, template_name=None):
    return JsonResponse({"message": "Not found.", "extra": {}}, status=404)


def handler500(request, template_name=None):
    # Deliberately says nothing about the exception: this is the unexpected-error path,
    # and DEBUG is off wherever it is reached.
    return JsonResponse({"message": "Server error.", "extra": {}}, status=500)
