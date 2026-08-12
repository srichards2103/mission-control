from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / ".env")

DEBUG = env("DEBUG", default=True)
# In DEBUG (local dev/test), fall back to a placeholder that is still >=32 bytes so it
# doesn't trip PyJWT's InsecureKeyLengthWarning for HS256. Outside DEBUG, there is no
# default: env("SECRET_KEY") raises ImproperlyConfigured if the env var is unset, so a
# deploy can never silently sign JWTs (and session/CSRF data) with this well-known,
# publicly-committed dev value.
SECRET_KEY = (
    env("SECRET_KEY", default="dev-only-insecure-key-do-not-use-in-prod")
    if DEBUG
    else env("SECRET_KEY")
)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "mission_control.common",
    "mission_control.tenants",
    "mission_control.users",
    "mission_control.missions",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "mission_control.tenants.middleware.TenantContextMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
TEMPLATES = []

DATABASES = {
    "default": env.db(
        "DATABASE_URL", default="postgres://mission:mission@localhost:5432/mission_control"
    )
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "users.User"
USE_TZ = True
TIME_ZONE = "UTC"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "mission_control.users.authentication.TenantJWTAuthentication"
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "EXCEPTION_HANDLER": "mission_control.common.exception_handler.exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}
