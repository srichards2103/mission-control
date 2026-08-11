from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.serializers import as_serializer_error
from rest_framework.views import exception_handler as _drf_exception_handler

from mission_control.common.exceptions import ApplicationError


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

    if isinstance(exc.detail, dict) and "detail" in exc.detail:
        # e.g. simplejwt's InvalidToken/AuthenticationFailed: {"detail": ..., "code": ...,
        # "messages": [...]}. Promote "detail" to the envelope message and keep the rest
        # (code, messages, ...) as extra, instead of stringifying the whole dict (which
        # produced an unreadable Python repr as the message).
        fields = dict(exc.detail)
        message = str(fields.pop("detail"))
        response.data = {"message": message, "extra": fields}
        return response

    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    response.data = {"message": detail, "extra": {}}
    return response
