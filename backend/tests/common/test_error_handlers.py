"""The error envelope has no holes: URLs that match nothing, and unexpected exceptions.

`common.exception_handler` covers everything DRF raises inside a view, but it returns
None for a non-DRF, non-`ApplicationError` exception (re-raising it into Django) and it
never sees a request that matched no URL pattern at all. Both of those used to render
Django's HTML error pages, so a client parsing `{"message", "extra"}` -- which the
frontend does on every failure -- got an HTML document instead.

These tests run with DEBUG off, which is the suite's default (see
`config.settings_test`) and the only configuration in which Django uses the handlers:
with DEBUG on it renders its technical 404/500 pages instead.
"""

import json

import pytest
from django.test import Client, override_settings
from django.urls import path

pytestmark = pytest.mark.django_db


def test_unmatched_url_returns_the_error_envelope_as_json(client):
    resp = client.get("/api/v1/bogus/")
    assert resp.status_code == 404
    assert resp["Content-Type"].startswith("application/json")
    assert json.loads(resp.content) == {"message": "Not found.", "extra": {}}


def test_unmatched_url_outside_the_api_prefix_too(client):
    resp = client.get("/nope")
    assert resp.status_code == 404
    assert json.loads(resp.content) == {"message": "Not found.", "extra": {}}


# --- handler500 needs a view that genuinely explodes, so this module doubles as a urlconf.


def _boom(request):
    raise RuntimeError("an exception the DRF handler declines")


urlpatterns = [path("boom/", _boom)]
handler404 = "config.urls.handler404"
handler500 = "config.urls.handler500"


@override_settings(ROOT_URLCONF=__name__)
def test_unhandled_exception_returns_the_error_envelope_as_json():
    # raise_request_exception=False: otherwise the test client re-raises the view's
    # exception instead of letting us inspect the response Django produced.
    resp = Client(raise_request_exception=False).get("/boom/")
    assert resp.status_code == 500
    assert resp["Content-Type"].startswith("application/json")
    assert json.loads(resp.content) == {"message": "Server error.", "extra": {}}
