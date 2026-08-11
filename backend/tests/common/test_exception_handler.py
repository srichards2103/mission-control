from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import serializers
from rest_framework.exceptions import NotAuthenticated, NotFound, PermissionDenied
from rest_framework_simplejwt.exceptions import InvalidToken

from mission_control.common.exception_handler import exception_handler
from mission_control.common.exceptions import ApplicationError


def test_application_error_becomes_400_envelope():
    exc = ApplicationError("Mission is not editable", extra={"status": "active"})
    resp = exception_handler(exc, {})
    assert resp.status_code == 400
    assert resp.data == {"message": "Mission is not editable", "extra": {"status": "active"}}


def test_validation_error_envelope():
    exc = serializers.ValidationError({"name": ["This field is required."]})
    resp = exception_handler(exc, {})
    assert resp.status_code == 400
    assert resp.data["message"] == "Validation error"
    assert resp.data["extra"]["fields"] == {"name": ["This field is required."]}


def test_permission_denied_envelope():
    resp = exception_handler(PermissionDenied(), {})
    assert resp.status_code == 403
    assert resp.data == {
        "message": "You do not have permission to perform this action.",
        "extra": {},
    }


def test_not_found_envelope():
    resp = exception_handler(NotFound(), {})
    assert resp.status_code == 404
    assert resp.data["extra"] == {}


def test_not_authenticated_envelope_and_www_authenticate_header():
    exc = NotAuthenticated()
    exc.auth_header = "Bearer"
    resp = exception_handler(exc, {})
    assert resp.status_code == 401
    assert resp.data == {
        "message": "Authentication credentials were not provided.",
        "extra": {},
    }
    assert resp["WWW-Authenticate"] == "Bearer"


def test_http404_envelope():
    resp = exception_handler(Http404(), {})
    assert resp.status_code == 404
    assert resp.data == {"message": "Not found.", "extra": {}}


def test_django_validation_error_envelope():
    exc = DjangoValidationError({"name": ["This field is required."]})
    resp = exception_handler(exc, {})
    assert resp.status_code == 400
    assert resp.data["message"] == "Validation error"
    assert resp.data["extra"]["fields"] == {"name": ["This field is required."]}


def test_bare_validation_error_wraps_non_dict_detail_as_non_field_errors():
    exc = serializers.ValidationError("Mission cannot be edited in this state.")
    resp = exception_handler(exc, {})
    assert resp.status_code == 400
    assert resp.data["message"] == "Validation error"
    assert resp.data["extra"]["fields"] == {
        "non_field_errors": ["Mission cannot be edited in this state."]
    }


def test_dict_detail_exception_promotes_detail_key_to_message():
    # simplejwt's InvalidToken (and other DetailDictMixin exceptions) carry a dict
    # detail like {"detail": "...", "code": "...", "messages": [...]}. Before this was
    # handled explicitly, `str(exc.detail)` stringified the whole dict into an
    # unreadable Python repr as the envelope "message".
    exc = InvalidToken()
    resp = exception_handler(exc, {})
    assert resp.status_code == 401
    assert resp.data["message"] == "Token is invalid or expired"
    assert resp.data["extra"]["code"] == "token_not_valid"
