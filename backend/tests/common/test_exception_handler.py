from rest_framework import serializers
from rest_framework.exceptions import NotFound, PermissionDenied

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
