from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.serializers import as_serializer_error

from mission_control.common.exceptions import ApplicationError

try:
    # Preferred path: DRF's own dispatch logic. This only succeeds once
    # mission_control/users/authentication.py exists (Task 1.5) — see the except
    # branch immediately below for why it doesn't exist yet.
    from rest_framework.views import exception_handler as _drf_exception_handler
except ImportError:
    # --- TODO(Task 1.5): delete this entire except branch. -----------------------
    # Once mission_control/users/authentication.py exists, the try above succeeds
    # unconditionally and this fallback is permanently unreachable dead code.
    #
    # Why it's needed for now: importing rest_framework.views unconditionally
    # imports rest_framework.schemas, which resolves
    # settings.REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] as a default-argument
    # expression AT IMPORT TIME. That setting points at
    # mission_control.users.authentication.TenantJWTAuthentication, which Task 1.5
    # creates — so today, the import above raises ImportError.
    #
    # This fallback is a byte-for-byte port of rest_framework.views.exception_handler
    # and set_rollback from the pinned DRF version (rest_framework/views.py:66-101),
    # used ONLY until Task 1.5 lands. It is not meant to track future DRF releases;
    # remove it rather than maintaining it once the try above works.
    from django.db import connections

    def _set_rollback():
        for db in connections.all(initialized_only=True):
            if db.settings_dict["ATOMIC_REQUESTS"] and db.in_atomic_block:
                db.set_rollback(True)

    def _drf_exception_handler(exc, ctx):
        if isinstance(exc, Http404):
            exc = exceptions.NotFound(*exc.args)
        elif isinstance(exc, DjangoPermissionDenied):
            exc = exceptions.PermissionDenied(*exc.args)

        if not isinstance(exc, exceptions.APIException):
            return None

        headers = {}
        if getattr(exc, "auth_header", None):
            headers["WWW-Authenticate"] = exc.auth_header
        if getattr(exc, "wait", None):
            headers["Retry-After"] = f"{exc.wait:d}"

        data = exc.detail if isinstance(exc.detail, (list, dict)) else {"detail": exc.detail}

        _set_rollback()
        return Response(data, status=exc.status_code, headers=headers)

    # -------------------------------------------------------------------------------


def exception_handler(exc, ctx):
    if isinstance(exc, DjangoValidationError):
        exc = exceptions.ValidationError(as_serializer_error(exc))
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()

    response = _drf_exception_handler(exc, ctx)
    if response is None:
        if isinstance(exc, ApplicationError):
            return Response({"message": exc.message, "extra": exc.extra}, status=400)
        return None  # unexpected -> 500

    # Reuse `response` (don't build a fresh Response) so any headers the dispatch
    # logic attached — WWW-Authenticate, Retry-After — survive onto the envelope.
    if isinstance(exc, exceptions.ValidationError):
        # exc.detail (-> response.data) is a dict for serializer/field errors, but a
        # bare `raise ValidationError("message")` (or a list of messages) yields a
        # list. extra["fields"] must always be an object per the global envelope
        # contract, so non-dict detail is coerced under "non_field_errors". Dict
        # detail passes through unchanged.
        if isinstance(response.data, dict):
            fields = response.data
        else:
            fields = {"non_field_errors": response.data}
        response.data = {"message": "Validation error", "extra": {"fields": fields}}
        return response

    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    response.data = {"message": detail, "extra": {}}
    return response
