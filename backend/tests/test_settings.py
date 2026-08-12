"""The settings module's fail-closed defaults.

`DEBUG` previously read `env("DEBUG", default=True)`. django-environ consults the
scheme default (`environ.Env(DEBUG=(bool, False))`) only when the call itself passes
none, so an *unset* DEBUG meant True -- which took the SECRET_KEY guard's dev branch
and signed every JWT with the publicly-committed key, on any deploy that forgot to set
DEBUG. These tests pin the default, and the guard that depends on it.

`config.settings` is exec'd under a probe module name with a scrubbed environment, so
the live `sys.modules["config.settings"]` (and the running Django configuration) is
untouched, and a developer's local `backend/.env` can't make the assertions pass or
fail for the wrong reason -- `read_env` is stubbed out.
"""

import importlib.util
import os
from pathlib import Path
from unittest import mock

import environ
import pytest
from django.core.exceptions import ImproperlyConfigured

SETTINGS_PATH = Path(__file__).resolve().parent.parent / "config" / "settings.py"
DEV_KEY = "dev-only-insecure-key-do-not-use-in-prod"


def _load_settings(**environment):
    spec = importlib.util.spec_from_file_location("config._settings_probe", SETTINGS_PATH)
    module = importlib.util.module_from_spec(spec)
    with (
        mock.patch.dict(os.environ, environment, clear=True),
        mock.patch.object(environ.Env, "read_env", lambda *a, **kw: None),
    ):
        spec.loader.exec_module(module)
    return module


def test_unset_debug_is_false_and_leaves_no_fallback_secret_key():
    with pytest.raises(ImproperlyConfigured):
        _load_settings()


def test_unset_debug_yields_production_shaped_defaults():
    settings = _load_settings(SECRET_KEY="a-real-deployment-key-at-least-32-bytes")
    assert settings.DEBUG is False
    assert settings.SECRET_KEY != DEV_KEY
    assert settings.ALLOWED_HOSTS == ["localhost", "127.0.0.1"]


def test_explicit_debug_true_still_gets_the_local_dev_fallback():
    settings = _load_settings(DEBUG="True")
    assert settings.DEBUG is True
    assert settings.SECRET_KEY == DEV_KEY


def test_explicit_values_win():
    settings = _load_settings(DEBUG="False", SECRET_KEY="k" * 40, ALLOWED_HOSTS="example.com")
    assert settings.DEBUG is False
    assert settings.ALLOWED_HOSTS == ["example.com"]
