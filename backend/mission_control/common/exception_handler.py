from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import connections
from django.http import Http404
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.serializers import as_serializer_error

from mission_control.common.exceptions import ApplicationError


def _set_rollback():
    """Mirror rest_framework.views.set_rollback without importing rest_framework.views.

    Importing rest_framework.views pulls in rest_framework.schemas, which resolves
    settings.REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] eagerly at import time.
    That path (mission_control.users.authentication.TenantJWTAuthentication) is only
    created in Task 1.5, so importing rest_framework.views here would break every
    caller of this exception handler until then. This module sticks to
    rest_framework.exceptions/response, which don't trigger that chain.
    """
    for db in connections.all(initialized_only=True):
        if db.settings_dict["ATOMIC_REQUESTS"] and db.in_atomic_block:
            db.set_rollback(True)


def _drf_exception_handler(exc, ctx):
    """Reimplementation of rest_framework.views.exception_handler (see _set_rollback)."""
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

    if isinstance(exc, exceptions.ValidationError):
        return Response(
            {"message": "Validation error", "extra": {"fields": response.data}},
            status=response.status_code,
        )
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return Response({"message": detail, "extra": {}}, status=response.status_code)
