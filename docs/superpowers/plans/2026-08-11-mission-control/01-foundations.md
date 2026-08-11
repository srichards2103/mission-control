# Stage 1: Foundations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Global constraints in `00-overview.md` apply to every task.

**Goal:** Runnable skeleton: Django backend with tenancy machinery, custom User + roles + permission catalog, JWT auth, error envelope; React frontend with login, route guards, app layout; Docker dev/prod; CI.

**Architecture:** Everything later stages depend on is defined here — tenant context, `TenantModel`, the permission catalog, the error envelope, the api-client. Get the interfaces exact.

**Tech Stack:** See `00-overview.md`.

---

### Task 1.1: Backend project scaffold + common app

**Files:**
- Create: `backend/pyproject.toml`, `backend/manage.py`, `backend/.env.example`, `backend/config/{__init__.py,settings.py,urls.py,wsgi.py}`, `backend/mission_control/__init__.py`, `backend/mission_control/common/{__init__.py,apps.py,models.py}`, `backend/tests/{__init__.py,conftest.py}`, `docker-compose.dev.yml` (db only for now), `.gitignore`

**Interfaces:**
- Produces: `mission_control.common.models.BaseModel` (abstract, `created_at`, `updated_at`); settings importable as `config.settings`; `uv run pytest` works from `backend/`.

- [ ] **Step 1: Create the scaffold files**

`backend/pyproject.toml`:

```toml
[project]
name = "mission-control-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "django>=5.2,<6.0",
    "djangorestframework>=3.16",
    "djangorestframework-simplejwt>=5.5",
    "psycopg[binary]>=3.2",
    "django-environ>=0.12",
    "gunicorn>=23.0",
]

[dependency-groups]
dev = ["pytest>=8.3", "pytest-django>=4.9", "factory-boy>=3.3", "ruff>=0.8"]

[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings"
python_files = ["test_*.py"]
addopts = "-q"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
```

`backend/manage.py` (standard django-admin template, `DJANGO_SETTINGS_MODULE=config.settings`).

`backend/config/settings.py`:

```python
from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="dev-only-insecure-key")
DEBUG = env("DEBUG", default=True)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "mission_control.common",
    "mission_control.tenants",
    "mission_control.users",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "mission_control.tenants.middleware.TenantContextMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
TEMPLATES = []

DATABASES = {"default": env.db("DATABASE_URL", default="postgres://mission:mission@localhost:5432/mission_control")}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "users.User"
USE_TZ = True
TIME_ZONE = "UTC"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["mission_control.users.authentication.TenantJWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "EXCEPTION_HANDLER": "mission_control.common.exception_handler.exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}
```

Note: `tenants`, `users` apps and the modules referenced by `REST_FRAMEWORK` are created in Tasks 1.2–1.5; until then Django won't boot — that's fine, first boot happens in Task 1.3 Step 5.

`backend/config/urls.py`:

```python
from django.urls import include, path

urlpatterns = [path("api/v1/", include("mission_control.users.urls"))]
```

`backend/mission_control/common/apps.py`:

```python
from django.apps import AppConfig

class CommonConfig(AppConfig):
    name = "mission_control.common"
```

`backend/mission_control/common/models.py`:

```python
from django.db import models

class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
```

`backend/tests/conftest.py`:

```python
import pytest
from rest_framework.test import APIClient

from mission_control.tenants.context import reset_current_tenant_id, set_current_tenant_id

TEST_PASSWORD = "password123"

@pytest.fixture(autouse=True)
def _clean_tenant_context():
    """Tests may set the tenant context directly; never let it leak into the next test."""
    token = set_current_tenant_id(None)
    yield
    reset_current_tenant_id(token)

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def auth_client_for(api_client):
    """Authenticate via the real JWT flow so the tenant context is set per-request."""
    def _make(user):
        resp = api_client.post("/api/v1/auth/token/", {"email": user.email, "password": TEST_PASSWORD})
        assert resp.status_code == 200, resp.content
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
        return client
    return _make
```

`docker-compose.dev.yml` (db service only; backend/frontend services added in Task 1.7):

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: mission
      POSTGRES_PASSWORD: mission
      POSTGRES_DB: mission_control
    ports: ["5432:5432"]
    volumes: [pgdata:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U mission"]
      interval: 2s
      retries: 20
volumes:
  pgdata:
```

`.gitignore`: standard Python (`__pycache__/`, `.venv/`, `.env`) + Node (`node_modules/`, `dist/`) + `.DS_Store`.

- [ ] **Step 2: Install deps and start the database**

```bash
cd backend && uv sync
docker compose -f ../docker-compose.dev.yml up -d db
```

Expected: lockfile created, db healthy (`docker compose -f ../docker-compose.dev.yml ps`).

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "chore: backend scaffold, common app, dev database"
```

---

### Task 1.2: Tenants app — context, model, scoped manager, middleware

**Files:**
- Create: `backend/mission_control/tenants/{__init__.py,apps.py,context.py,models.py,middleware.py}`, `backend/tests/tenants/{__init__.py,test_context.py}`

**Interfaces:**
- Produces:
  - `tenants.context`: `set_current_tenant_id(tenant_id: int) -> Token`, `reset_current_tenant_id(token)`, `get_current_tenant_id() -> int | None`, `require_current_tenant_id() -> int` (raises `TenantContextNotSet`)
  - `tenants.models.Tenant` (`name: str`, `slug: str` unique)
  - `tenants.models.TenantModel` (abstract): `tenant` FK (PROTECT), default manager `objects` = tenant-scoped fail-closed, `objects_unscoped`, auto-stamps `tenant_id` on first save
  - `tenants.middleware.TenantContextMiddleware`

- [ ] **Step 1: Write the failing tests**

`backend/tests/tenants/test_context.py`:

```python
import pytest
from django.http import HttpResponse
from django.test import RequestFactory

from mission_control.tenants.context import (
    TenantContextNotSet,
    get_current_tenant_id,
    require_current_tenant_id,
    reset_current_tenant_id,
    set_current_tenant_id,
)
from mission_control.tenants.middleware import TenantContextMiddleware


def test_require_raises_when_unset():
    assert get_current_tenant_id() is None
    with pytest.raises(TenantContextNotSet):
        require_current_tenant_id()


def test_set_and_reset_roundtrip():
    token = set_current_tenant_id(42)
    assert require_current_tenant_id() == 42
    reset_current_tenant_id(token)
    assert get_current_tenant_id() is None


def test_middleware_clears_context_after_request():
    def view(request):
        set_current_tenant_id(7)  # what the JWT auth class will do
        assert get_current_tenant_id() == 7
        return HttpResponse()

    middleware = TenantContextMiddleware(view)
    middleware(RequestFactory().get("/"))
    assert get_current_tenant_id() is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/tenants/ -v` — Expected: FAIL (`ModuleNotFoundError: mission_control.tenants.context`).

- [ ] **Step 3: Implement**

`backend/mission_control/tenants/apps.py`: `TenantsConfig(AppConfig)` with `name = "mission_control.tenants"`.

`backend/mission_control/tenants/context.py`:

```python
from contextvars import ContextVar, Token

_current_tenant_id: ContextVar[int | None] = ContextVar("current_tenant_id", default=None)


class TenantContextNotSet(Exception):
    """A tenant-scoped operation ran with no tenant in context. Fail closed."""


def set_current_tenant_id(tenant_id: int | None) -> Token:
    return _current_tenant_id.set(tenant_id)


def reset_current_tenant_id(token: Token) -> None:
    _current_tenant_id.reset(token)


def get_current_tenant_id() -> int | None:
    return _current_tenant_id.get()


def require_current_tenant_id() -> int:
    tenant_id = _current_tenant_id.get()
    if tenant_id is None:
        raise TenantContextNotSet("No tenant in context; refusing unscoped access to tenant data.")
    return tenant_id
```

`backend/mission_control/tenants/middleware.py`:

```python
from mission_control.tenants.context import reset_current_tenant_id, set_current_tenant_id


class TenantContextMiddleware:
    """Guarantees the tenant context never leaks between requests (incl. on exceptions)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = set_current_tenant_id(None)
        try:
            return self.get_response(request)
        finally:
            reset_current_tenant_id(token)
```

`backend/mission_control/tenants/models.py`:

```python
from django.db import models

from mission_control.common.models import BaseModel
from mission_control.tenants.context import require_current_tenant_id


class Tenant(BaseModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=64, unique=True)

    def __str__(self):
        return self.slug


class TenantManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(tenant_id=require_current_tenant_id())


class TenantModel(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, related_name="+")

    objects = TenantManager()
    objects_unscoped = models.Manager()

    class Meta:
        abstract = True
        base_manager_name = "objects_unscoped"

    def save(self, *args, **kwargs):
        if self.tenant_id is None:
            self.tenant_id = require_current_tenant_id()
        super().save(*args, **kwargs)
```

(`base_manager_name = "objects_unscoped"` keeps FK traversal/save internals off the scoped manager; DB-level tests for the scoped manager land with the first concrete `TenantModel` in Stage 2 Task 2.1.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/tenants/ -v` — Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: tenant context, TenantModel with fail-closed scoped manager, middleware"
```

---

### Task 1.3: Users app — User model, roles, permission catalog

**Files:**
- Create: `backend/mission_control/users/{__init__.py,apps.py,models.py,roles.py,permissions.py,factories.py}`, `backend/tests/users/{__init__.py,test_roles.py}`
- Create (generated): `backend/mission_control/tenants/migrations/0001_initial.py`, `backend/mission_control/users/migrations/0001_initial.py`

**Interfaces:**
- Produces:
  - `users.models.User`: `email` (unique, USERNAME_FIELD), `name`, `tenant` FK, `role`, `is_active`; **standard** manager `objects` (`User.objects.create_user(email=..., password=..., tenant=..., role=..., name=...)`). Meta constraint `UNIQUE(tenant, id)` named `users_user_tenant_id_uniq`.
  - `users.roles.Role` (TextChoices): `DIRECTOR = "director"`, `MISSION_LEAD = "mission_lead"`, `CREW_MEMBER = "crew_member"`
  - `users.permissions.Permission` (StrEnum) — 16 values listed below; `permissions_for_role(role: str) -> frozenset[Permission]`; `ensure_permission(user, perm)` raises DRF `PermissionDenied`; `HasPermission(perm) -> type[BasePermission]` for `permission_classes`.
  - `users.factories.TenantFactory`, `users.factories.UserFactory` (password = `password123`)

- [ ] **Step 1: Write the failing tests**

`backend/tests/users/test_roles.py`:

```python
import pytest
from rest_framework.exceptions import PermissionDenied

from mission_control.users.factories import UserFactory
from mission_control.users.permissions import Permission, ensure_permission, permissions_for_role
from mission_control.users.roles import Role


def test_director_has_everything_except_crew_self_service():
    perms = permissions_for_role(Role.DIRECTOR)
    assert Permission.MISSION_REVIEW in perms
    assert Permission.SETTINGS_MANAGE in perms
    assert Permission.ASSIGNMENT_RESPOND not in perms
    assert Permission.OWN_SKILLS_EDIT not in perms
    assert len(perms) == 14


def test_mission_lead_set_exact():
    assert permissions_for_role(Role.MISSION_LEAD) == frozenset({
        Permission.MISSION_VIEW, Permission.MISSION_CREATE, Permission.MISSION_EDIT,
        Permission.MISSION_PROGRESS, Permission.ASSIGNMENT_MANAGE, Permission.MATCH_RUN,
        Permission.CREW_VIEW, Permission.SKILL_VIEW, Permission.DASHBOARD_VIEW,
    })


def test_crew_member_set_exact():
    assert permissions_for_role(Role.CREW_MEMBER) == frozenset({
        Permission.SKILL_VIEW, Permission.OWN_SKILLS_EDIT, Permission.ASSIGNMENT_RESPOND,
    })


@pytest.mark.django_db
def test_ensure_permission_raises_for_missing():
    crew = UserFactory(role=Role.CREW_MEMBER)
    ensure_permission(crew, Permission.OWN_SKILLS_EDIT)  # no raise
    with pytest.raises(PermissionDenied):
        ensure_permission(crew, Permission.MISSION_CREATE)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/users/ -v` — Expected: FAIL (modules missing).

- [ ] **Step 3: Implement**

`backend/mission_control/users/roles.py`:

```python
from django.db import models


class Role(models.TextChoices):
    DIRECTOR = "director", "Director"
    MISSION_LEAD = "mission_lead", "Mission Lead"
    CREW_MEMBER = "crew_member", "Crew Member"
```

`backend/mission_control/users/permissions.py`:

```python
from enum import StrEnum

from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from mission_control.users.roles import Role


class Permission(StrEnum):
    MISSION_VIEW = "mission.view"
    MISSION_CREATE = "mission.create"
    MISSION_EDIT = "mission.edit"
    MISSION_PROGRESS = "mission.progress"
    MISSION_REVIEW = "mission.review"
    ASSIGNMENT_MANAGE = "assignment.manage"
    ASSIGNMENT_RESPOND = "assignment.respond"
    MATCH_RUN = "match.run"
    CREW_VIEW = "crew.view"
    USER_MANAGE = "user.manage"
    SKILL_VIEW = "skill.view"
    SKILL_MANAGE = "skill.manage"
    OWN_SKILLS_EDIT = "own_skills.edit"
    SETTINGS_VIEW = "settings.view"
    SETTINGS_MANAGE = "settings.manage"
    DASHBOARD_VIEW = "dashboard.view"


_CREW = frozenset({Permission.SKILL_VIEW, Permission.OWN_SKILLS_EDIT, Permission.ASSIGNMENT_RESPOND})
_LEAD = frozenset({
    Permission.MISSION_VIEW, Permission.MISSION_CREATE, Permission.MISSION_EDIT,
    Permission.MISSION_PROGRESS, Permission.ASSIGNMENT_MANAGE, Permission.MATCH_RUN,
    Permission.CREW_VIEW, Permission.SKILL_VIEW, Permission.DASHBOARD_VIEW,
})
_DIRECTOR = frozenset(Permission) - {Permission.ASSIGNMENT_RESPOND, Permission.OWN_SKILLS_EDIT}

ROLE_PERMISSIONS: dict[str, frozenset[Permission]] = {
    Role.DIRECTOR: _DIRECTOR,
    Role.MISSION_LEAD: _LEAD,
    Role.CREW_MEMBER: _CREW,
}


def permissions_for_role(role: str) -> frozenset[Permission]:
    return ROLE_PERMISSIONS[role]


def user_has_permission(user, perm: Permission) -> bool:
    return perm in permissions_for_role(user.role)


def ensure_permission(user, perm: Permission) -> None:
    if not user_has_permission(user, perm):
        raise PermissionDenied


def HasPermission(perm: Permission) -> type[BasePermission]:
    class _HasPermission(BasePermission):
        def has_permission(self, request, view):
            return user_has_permission(request.user, perm)

    return _HasPermission
```

`backend/mission_control/users/models.py`:

```python
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models

from mission_control.common.models import BaseModel
from mission_control.users.roles import Role


class UserManager(BaseUserManager):
    def create_user(self, *, email, password, tenant, role, name):
        user = self.model(email=self.normalize_email(email), tenant=tenant, role=role, name=name)
        user.set_password(password)
        user.save()
        return user


class User(AbstractBaseUser, BaseModel):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT, related_name="users")
    role = models.CharField(max_length=32, choices=Role.choices)
    is_active = models.BooleanField(default=True)

    objects = UserManager()  # standard manager: auth resolves users before tenant context exists

    USERNAME_FIELD = "email"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "id"], name="users_user_tenant_id_uniq"),
        ]

    def __str__(self):
        return self.email
```

`backend/mission_control/users/factories.py`:

```python
import factory

from mission_control.tenants.models import Tenant
from mission_control.users.models import User
from mission_control.users.roles import Role


class TenantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tenant

    name = factory.Sequence(lambda n: f"Tenant {n}")
    slug = factory.Sequence(lambda n: f"tenant-{n}")


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    name = factory.Sequence(lambda n: f"User {n}")
    tenant = factory.SubFactory(TenantFactory)
    role = Role.CREW_MEMBER
    password = factory.PostGenerationMethodCall("set_password", "password123")
```

`backend/mission_control/users/apps.py`: `UsersConfig` with `name = "mission_control.users"`.

- [ ] **Step 4: Generate migrations, run tests**

```bash
uv run python manage.py makemigrations tenants users
uv run pytest tests/ -v
```

Expected: two `0001_initial.py` created; all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: custom User, Role enum, 16-permission catalog with role sets"
```

---

### Task 1.4: Error envelope + pagination

**Files:**
- Create: `backend/mission_control/common/{exceptions.py,exception_handler.py,pagination.py}`, `backend/tests/common/{__init__.py,test_exception_handler.py}`

**Interfaces:**
- Produces:
  - `common.exceptions.ApplicationError(message: str, extra: dict | None = None)`
  - `common.exception_handler.exception_handler` (already wired in settings)
  - `common.pagination.get_paginated_response(*, serializer_class, queryset, request) -> Response` — body `{"results", "count", "limit", "offset"}`, query params `limit` (default 25, max 100) & `offset`

- [ ] **Step 1: Write the failing tests**

`backend/tests/common/test_exception_handler.py`:

```python
from rest_framework import serializers
from rest_framework.exceptions import NotFound, PermissionDenied

from mission_control.common.exception_handler import exception_handler
from mission_control.common.exceptions import ApplicationError


def test_application_error_becomes_400_envelope():
    resp = exception_handler(ApplicationError("Mission is not editable", extra={"status": "active"}), {})
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
    assert resp.data == {"message": "You do not have permission to perform this action.", "extra": {}}


def test_not_found_envelope():
    resp = exception_handler(NotFound(), {})
    assert resp.status_code == 404
    assert resp.data["extra"] == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/common/ -v` — Expected: FAIL (modules missing).

- [ ] **Step 3: Implement**

`backend/mission_control/common/exceptions.py`:

```python
class ApplicationError(Exception):
    def __init__(self, message: str, extra: dict | None = None):
        super().__init__(message)
        self.message = message
        self.extra = extra or {}
```

`backend/mission_control/common/exception_handler.py`:

```python
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.serializers import as_serializer_error
from rest_framework.views import exception_handler as drf_exception_handler

from mission_control.common.exceptions import ApplicationError


def exception_handler(exc, ctx):
    if isinstance(exc, DjangoValidationError):
        exc = exceptions.ValidationError(as_serializer_error(exc))
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()

    response = drf_exception_handler(exc, ctx)
    if response is None:
        if isinstance(exc, ApplicationError):
            return Response({"message": exc.message, "extra": exc.extra}, status=400)
        return None  # unexpected -> 500

    if isinstance(exc, exceptions.ValidationError):
        return Response({"message": "Validation error", "extra": {"fields": response.data}},
                        status=response.status_code)
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return Response({"message": detail, "extra": {}}, status=response.status_code)
```

`backend/mission_control/common/pagination.py`:

```python
from rest_framework.pagination import LimitOffsetPagination


class ApiPagination(LimitOffsetPagination):
    default_limit = 25
    max_limit = 100


def get_paginated_response(*, serializer_class, queryset, request):
    paginator = ApiPagination()
    page = paginator.paginate_queryset(queryset, request)
    from rest_framework.response import Response

    return Response({
        "results": serializer_class(page, many=True).data,
        "count": paginator.count,
        "limit": paginator.limit,
        "offset": paginator.offset,
    })
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/common/ -v` — Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: ApplicationError, global exception envelope, pagination helper"
```

---

### Task 1.5: JWT auth — tenant-binding authentication + /auth/me

**Files:**
- Create: `backend/mission_control/users/authentication.py`, `backend/mission_control/users/apis/{__init__.py,auth.py}`, `backend/mission_control/users/urls.py`, `backend/tests/users/test_auth_api.py`

**Interfaces:**
- Produces:
  - `users.authentication.TenantJWTAuthentication` — sets tenant context after token→user resolution; rejects inactive users
  - `POST /api/v1/auth/token/` `{email, password}` → `{access, refresh}` · `POST /api/v1/auth/token/refresh/` `{refresh}` → `{access, refresh}`
  - `GET /api/v1/auth/me/` → `{id, email, name, role, tenant: {id, name, slug}, permissions: [str]}`

- [ ] **Step 1: Write the failing tests**

`backend/tests/users/test_auth_api.py`:

```python
import pytest

from mission_control.users.factories import UserFactory
from mission_control.users.roles import Role

pytestmark = pytest.mark.django_db


def test_token_obtain_and_me(api_client, auth_client_for):
    user = UserFactory(role=Role.MISSION_LEAD)
    client = auth_client_for(user)
    resp = client.get("/api/v1/auth/me/")
    assert resp.status_code == 200
    assert resp.data["email"] == user.email
    assert resp.data["role"] == "mission_lead"
    assert resp.data["tenant"]["slug"] == user.tenant.slug
    assert "mission.create" in resp.data["permissions"]
    assert "mission.review" not in resp.data["permissions"]


def test_bad_password_gets_envelope(api_client):
    user = UserFactory()
    resp = api_client.post("/api/v1/auth/token/", {"email": user.email, "password": "wrong"})
    assert resp.status_code == 401
    assert set(resp.data) == {"message", "extra"}


def test_me_requires_auth(api_client):
    assert api_client.get("/api/v1/auth/me/").status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/users/test_auth_api.py -v` — Expected: FAIL (404s / import errors).

- [ ] **Step 3: Implement**

`backend/mission_control/users/authentication.py`:

```python
from rest_framework_simplejwt.authentication import JWTAuthentication

from mission_control.tenants.context import set_current_tenant_id


class TenantJWTAuthentication(JWTAuthentication):
    """Binds the tenant context to the authenticated user for the rest of the request."""

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is not None:
            user, _token = result
            set_current_tenant_id(user.tenant_id)
        return result
```

`backend/mission_control/users/apis/auth.py`:

```python
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from mission_control.users.permissions import permissions_for_role


class MeApi(APIView):
    class OutputSerializer(serializers.Serializer):
        id = serializers.IntegerField()
        email = serializers.EmailField()
        name = serializers.CharField()
        role = serializers.CharField()
        tenant = serializers.SerializerMethodField()
        permissions = serializers.SerializerMethodField()

        def get_tenant(self, user):
            return {"id": user.tenant.id, "name": user.tenant.name, "slug": user.tenant.slug}

        def get_permissions(self, user):
            return sorted(p.value for p in permissions_for_role(user.role))

    def get(self, request):
        return Response(self.OutputSerializer(request.user).data)
```

`backend/mission_control/users/urls.py`:

```python
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from mission_control.users.apis.auth import MeApi

urlpatterns = [
    path("auth/token/", TokenObtainPairView.as_view()),
    path("auth/token/refresh/", TokenRefreshView.as_view()),
    path("auth/me/", MeApi.as_view()),
]
```

- [ ] **Step 4: Migrate (token_blacklist) and run all tests**

```bash
uv run python manage.py migrate
uv run pytest tests/ -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: JWT auth with tenant-binding authentication and /auth/me"
```

---

### Task 1.6: Seed skeleton

**Files:**
- Create: `backend/mission_control/users/management/{__init__.py,commands/__init__.py,commands/seed_demo.py}`, `backend/tests/users/test_seed.py`

**Interfaces:**
- Produces: `manage.py seed_demo` — idempotent; creates tenants `helios-aerospace` ("Helios Aerospace") and `meridian-orbital` ("Meridian Orbital"), and per tenant: `director@<slug>.test`, `lead@<slug>.test`, `crew1@<slug>.test` (password `orbit-demo-2026` for all). Later stages extend this command in place.

- [ ] **Step 1: Write the failing test**

`backend/tests/users/test_seed.py`:

```python
import pytest
from django.core.management import call_command

from mission_control.tenants.models import Tenant
from mission_control.users.models import User

pytestmark = pytest.mark.django_db


def test_seed_demo_idempotent():
    call_command("seed_demo")
    call_command("seed_demo")
    assert Tenant.objects.count() == 2
    assert User.objects.filter(email="director@helios-aerospace.test").exists()
    assert User.objects.count() == 6
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/users/test_seed.py -v` — Expected: FAIL (unknown command).

- [ ] **Step 3: Implement**

`backend/mission_control/users/management/commands/seed_demo.py`:

```python
from django.core.management.base import BaseCommand

from mission_control.tenants.models import Tenant
from mission_control.users.models import User
from mission_control.users.roles import Role

DEMO_PASSWORD = "orbit-demo-2026"
TENANTS = [("Helios Aerospace", "helios-aerospace"), ("Meridian Orbital", "meridian-orbital")]
ROLES = [("director", Role.DIRECTOR), ("lead", Role.MISSION_LEAD), ("crew1", Role.CREW_MEMBER)]


class Command(BaseCommand):
    help = "Seed demo tenants and users (idempotent)."

    def handle(self, *args, **options):
        for name, slug in TENANTS:
            tenant, _ = Tenant.objects.get_or_create(slug=slug, defaults={"name": name})
            for prefix, role in ROLES:
                email = f"{prefix}@{slug}.test"
                if not User.objects.filter(email=email).exists():
                    User.objects.create_user(
                        email=email, password=DEMO_PASSWORD, tenant=tenant,
                        role=role, name=f"{prefix.title()} {name.split()[0]}",
                    )
        self.stdout.write(self.style.SUCCESS("Seeded demo data."))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/users/test_seed.py -v` — Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: seed_demo command with demo tenants and role users"
```

---

### Task 1.7: Docker (dev + prod) and CI

**Files:**
- Create: `backend/Dockerfile`, `frontend/Dockerfile` (frontend dir exists after Task 1.8 — CI's frontend job will fail until then; acceptable within the stage), `nginx.conf`, `docker-compose.yml`, `.github/workflows/ci.yml`
- Modify: `docker-compose.dev.yml` (add backend + frontend services)

**Interfaces:**
- Produces: `docker compose -f docker-compose.dev.yml up` = full dev stack (db + runserver + vite on :5173); `docker compose up` = prod stack on :80.

- [ ] **Step 1: Write the files**

`backend/Dockerfile`:

```dockerfile
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY . .
CMD ["uv", "run", "gunicorn", "config.wsgi", "--bind", "0.0.0.0:8000"]
```

`docker-compose.dev.yml` — add:

```yaml
  backend:
    build: ./backend
    command: sh -c "uv sync && uv run python manage.py migrate && uv run python manage.py seed_demo && uv run python manage.py runserver 0.0.0.0:8000"
    volumes: ["./backend:/app"]
    environment:
      DATABASE_URL: postgres://mission:mission@db:5432/mission_control
    ports: ["8000:8000"]
    depends_on:
      db: {condition: service_healthy}
  frontend:
    image: node:22-alpine
    working_dir: /app
    command: sh -c "npm install && npm run dev -- --host"
    volumes: ["./frontend:/app"]
    environment:
      VITE_PROXY_TARGET: http://backend:8000
    ports: ["5173:5173"]
```

`docker-compose.yml` (prod):

```yaml
services:
  db:
    image: postgres:16
    environment: {POSTGRES_USER: mission, POSTGRES_PASSWORD: mission, POSTGRES_DB: mission_control}
    volumes: [pgdata:/var/lib/postgresql/data]
    healthcheck: {test: ["CMD-SHELL", "pg_isready -U mission"], interval: 2s, retries: 20}
  backend:
    build: ./backend
    command: sh -c "uv run python manage.py migrate && uv run python manage.py seed_demo && uv run gunicorn config.wsgi --bind 0.0.0.0:8000"
    environment:
      DATABASE_URL: postgres://mission:mission@db:5432/mission_control
      DEBUG: "false"
      SECRET_KEY: change-me-in-real-deploys
      ALLOWED_HOSTS: "*"
    depends_on:
      db: {condition: service_healthy}
  web:
    build: ./frontend
    ports: ["80:80"]
    depends_on: [backend]
volumes:
  pgdata:
```

`frontend/Dockerfile`:

```dockerfile
FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY ../nginx.conf /etc/nginx/conf.d/default.conf
```

Note: nginx.conf must be inside the frontend build context — place a copy at `frontend/nginx.conf` and use `COPY nginx.conf /etc/nginx/conf.d/default.conf` instead. `frontend/nginx.conf`:

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    location /api/ { proxy_pass http://backend:8000; proxy_set_header Host $host; }
    location / { try_files $uri /index.html; }
}
```

`.github/workflows/ci.yml`:

```yaml
name: CI
on: [push, pull_request]
jobs:
  backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env: {POSTGRES_USER: mission, POSTGRES_PASSWORD: mission, POSTGRES_DB: mission_control}
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U mission" --health-interval 2s --health-retries 20
    defaults: {run: {working-directory: backend}}
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync
      - run: uv run ruff check .
      - run: uv run pytest
  frontend:
    runs-on: ubuntu-latest
    defaults: {run: {working-directory: frontend}}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: {node-version: 22}
      - run: npm ci
      - run: npm run lint
      - run: npm test -- --run
      - run: npm run build
```

- [ ] **Step 2: Verify backend image builds**

Run: `docker compose build backend` — Expected: success.

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "chore: docker dev/prod stacks and GitHub Actions CI"
```

---

### Task 1.8: Frontend scaffold + api-client

**Files:**
- Create: `frontend/` via Vite (react-ts template), then `frontend/src/lib/api-client.ts`, `frontend/vite.config.ts`, `frontend/src/testing/setup.ts`, `frontend/src/lib/api-client.test.ts`

**Interfaces:**
- Produces:
  - `lib/api-client.ts`: `api` (axios instance, baseURL `/api/v1`), `setTokens(access, refresh)`, `clearTokens()`, `getAccessToken()` — access in module memory, refresh in `localStorage.mc_refresh`; response interceptor: on 401 (not from `/auth/token`), POST `/api/v1/auth/token/refresh/` once, retry original; on failure `clearTokens()` and `window.location.assign("/login")`.
  - Test tooling: `npm test` (vitest, jsdom), `npm run lint`, `npm run build`.
  - shadcn/ui installed with components: `button card input label table dialog tabs badge select popover sonner skeleton`.

- [ ] **Step 1: Scaffold**

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm i axios zod @tanstack/react-query react-router-dom
npm i -D vitest jsdom @testing-library/react @testing-library/user-event @testing-library/jest-dom msw
npm i tailwindcss @tailwindcss/vite
npx shadcn@latest init -d
npx shadcn@latest add button card input label table dialog tabs badge select popover sonner skeleton
```

`frontend/vite.config.ts`:

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
  server: {
    proxy: { "/api": { target: process.env.VITE_PROXY_TARGET ?? "http://localhost:8000" } },
  },
  test: { environment: "jsdom", setupFiles: "./src/testing/setup.ts", globals: true },
});
```

Add to `package.json` scripts: `"test": "vitest"`. `src/testing/setup.ts`: `import "@testing-library/jest-dom";`

- [ ] **Step 2: Write the failing api-client test**

`frontend/src/lib/api-client.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { clearTokens, getAccessToken, setTokens } from "./api-client";

describe("token store", () => {
  it("keeps access in memory and refresh in localStorage", () => {
    setTokens("acc-1", "ref-1");
    expect(getAccessToken()).toBe("acc-1");
    expect(localStorage.getItem("mc_refresh")).toBe("ref-1");
    clearTokens();
    expect(getAccessToken()).toBeNull();
    expect(localStorage.getItem("mc_refresh")).toBeNull();
  });
});
```

Run: `npm test -- --run` — Expected: FAIL (module missing).

- [ ] **Step 3: Implement `frontend/src/lib/api-client.ts`**

```ts
import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";

let accessToken: string | null = null;
const REFRESH_KEY = "mc_refresh";

export function setTokens(access: string, refresh: string) {
  accessToken = access;
  localStorage.setItem(REFRESH_KEY, refresh);
}
export function clearTokens() {
  accessToken = null;
  localStorage.removeItem(REFRESH_KEY);
}
export function getAccessToken() {
  return accessToken;
}
export function getRefreshToken() {
  return localStorage.getItem(REFRESH_KEY);
}

export const api = axios.create({ baseURL: "/api/v1" });

api.interceptors.request.use((config) => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`;
  return config;
});

api.interceptors.response.use(undefined, async (error: AxiosError) => {
  const original = error.config as InternalAxiosRequestConfig & { _retried?: boolean };
  const refresh = getRefreshToken();
  if (error.response?.status === 401 && refresh && !original._retried &&
      !original.url?.includes("/auth/token")) {
    original._retried = true;
    try {
      const { data } = await axios.post("/api/v1/auth/token/refresh/", { refresh });
      setTokens(data.access, data.refresh);
      return api(original);
    } catch {
      clearTokens();
      window.location.assign("/login");
    }
  }
  throw error;
});
```

- [ ] **Step 4: Verify green**

Run: `npm test -- --run && npm run build` — Expected: PASS + successful build.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: frontend scaffold with shadcn, api client with token refresh"
```

---

### Task 1.9: Auth feature — login, guards, app shell

**Files:**
- Create: `frontend/src/features/auth/api/auth.ts`, `frontend/src/features/auth/components/login-form.tsx`, `frontend/src/lib/auth.tsx`, `frontend/src/components/layout/app-layout.tsx`, `frontend/src/app/{provider.tsx,router.tsx}`, `frontend/src/testing/mocks.ts`, `frontend/src/features/auth/auth.test.tsx`
- Modify: `frontend/src/main.tsx`

**Interfaces:**
- Produces:
  - `features/auth/api/auth.ts`: `UserSchema` (zod: `id, email, name, role, tenant{id,name,slug}, permissions: string[]`), `login(email, password)` (POST `/auth/token/` then stores tokens), `fetchMe(): Promise<User>` (zod-parsed)
  - `lib/auth.tsx`: `useUser()` (react-query `["auth","me"]`), `useLogout()`, `hasPermission(user, perm: string): boolean`, `<ProtectedRoute/>` (outlet or redirect `/login`), `<RequirePermission permission>` (children or `<Navigate to="/" />`)
  - `app/router.tsx`: routes `/login`, and protected shell with placeholder pages: `/` (Dashboard), `/missions`, `/crew`, `/my-assignments`, `/my-profile`, `/settings` — each later stage replaces its placeholder. Nav items rendered only when `hasPermission` passes: Dashboard→`dashboard.view`, Missions→`mission.view`, Crew→`crew.view`, My Assignments→`assignment.respond`, My Profile→`own_skills.edit`, Settings→`settings.view`. `/` redirects to `/my-assignments` when the user lacks `dashboard.view`.

- [ ] **Step 1: Write the failing tests**

`frontend/src/testing/mocks.ts`:

```ts
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";

export const leadUser = {
  id: 1, email: "lead@helios.test", name: "Lead", role: "mission_lead",
  tenant: { id: 1, name: "Helios", slug: "helios" },
  permissions: ["mission.view", "mission.create", "mission.edit", "mission.progress",
    "assignment.manage", "match.run", "crew.view", "skill.view", "dashboard.view"],
};
export const crewUser = {
  ...leadUser, id: 2, email: "crew@helios.test", role: "crew_member",
  permissions: ["skill.view", "own_skills.edit", "assignment.respond"],
};

export const server = setupServer(
  http.post("/api/v1/auth/token/", () => HttpResponse.json({ access: "a", refresh: "r" })),
  http.get("/api/v1/auth/me/", () => HttpResponse.json(leadUser)),
);
```

Add to `src/testing/setup.ts`:

```ts
import "@testing-library/jest-dom";
import { server } from "./mocks";

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

`frontend/src/features/auth/auth.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { AppProvider } from "@/app/provider";
import { createRouter } from "@/app/router";
import { RouterProvider } from "react-router-dom";
import { crewUser, server } from "@/testing/mocks";

function renderApp(path = "/") {
  const router = createRouter([path]);
  render(
    <AppProvider>
      <RouterProvider router={router} />
    </AppProvider>,
  );
}

describe("auth shell", () => {
  it("logs in and shows lead nav", async () => {
    renderApp("/login");
    await userEvent.type(await screen.findByLabelText(/email/i), "lead@helios.test");
    await userEvent.type(screen.getByLabelText(/password/i), "pw");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
    expect(await screen.findByRole("link", { name: /missions/i })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /settings/i })).not.toBeInTheDocument();
  });

  it("crew member is redirected from / to my-assignments", async () => {
    server.use(http.get("/api/v1/auth/me/", () => HttpResponse.json(crewUser)));
    renderApp("/");
    expect(await screen.findByRole("heading", { name: /my assignments/i })).toBeInTheDocument();
  });
});
```

Run: `npm test -- --run` — Expected: FAIL (modules missing).

- [ ] **Step 2: Implement**

`frontend/src/features/auth/api/auth.ts`:

```ts
import { z } from "zod";
import { api, setTokens } from "@/lib/api-client";

export const UserSchema = z.object({
  id: z.number(),
  email: z.string(),
  name: z.string(),
  role: z.enum(["director", "mission_lead", "crew_member"]),
  tenant: z.object({ id: z.number(), name: z.string(), slug: z.string() }),
  permissions: z.array(z.string()),
});
export type User = z.infer<typeof UserSchema>;

export async function login(email: string, password: string) {
  const { data } = await api.post("/auth/token/", { email, password });
  setTokens(data.access, data.refresh);
}

export async function fetchMe(): Promise<User> {
  const { data } = await api.get("/auth/me/");
  return UserSchema.parse(data);
}
```

`frontend/src/lib/auth.tsx`:

```tsx
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Navigate, Outlet } from "react-router-dom";
import { fetchMe, type User } from "@/features/auth/api/auth";
import { clearTokens } from "@/lib/api-client";

export function useUser() {
  return useQuery({ queryKey: ["auth", "me"], queryFn: fetchMe, retry: false, staleTime: 5 * 60_000 });
}

export function useLogout() {
  const qc = useQueryClient();
  return () => {
    clearTokens();
    qc.clear();
    window.location.assign("/login");
  };
}

export function hasPermission(user: User | undefined, perm: string) {
  return !!user?.permissions.includes(perm);
}

export function ProtectedRoute() {
  const { data: user, isLoading, isError } = useUser();
  if (isLoading) return null;
  if (isError || !user) return <Navigate to="/login" replace />;
  return <Outlet />;
}

export function RequirePermission({ permission, children }: { permission: string; children: React.ReactNode }) {
  const { data: user } = useUser();
  if (!hasPermission(user, permission)) return <Navigate to="/" replace />;
  return <>{children}</>;
}
```

`frontend/src/features/auth/components/login-form.tsx` — card with labelled email + password inputs and a "Sign in" button; on submit `login()` then `navigate("/")`; on failure show the API envelope `message` under the form. Use shadcn `Card/Input/Label/Button`, `useState` for fields.

`frontend/src/components/layout/app-layout.tsx`:

```tsx
import { NavLink, Outlet } from "react-router-dom";
import { hasPermission, useLogout, useUser } from "@/lib/auth";

const NAV = [
  { to: "/", label: "Dashboard", perm: "dashboard.view" },
  { to: "/missions", label: "Missions", perm: "mission.view" },
  { to: "/crew", label: "Crew", perm: "crew.view" },
  { to: "/my-assignments", label: "My Assignments", perm: "assignment.respond" },
  { to: "/my-profile", label: "My Profile", perm: "own_skills.edit" },
  { to: "/settings", label: "Settings", perm: "settings.view" },
];

export function AppLayout() {
  const { data: user } = useUser();
  const logout = useLogout();
  return (
    <div className="flex min-h-screen">
      <aside className="w-56 border-r p-4 flex flex-col gap-1">
        <div className="font-semibold mb-4">{user?.tenant.name}</div>
        {NAV.filter((n) => hasPermission(user, n.perm)).map((n) => (
          <NavLink key={n.to} to={n.to} className="rounded px-2 py-1 text-sm hover:bg-accent">
            {n.label}
          </NavLink>
        ))}
        <button onClick={logout} className="mt-auto text-left text-sm text-muted-foreground px-2">
          Sign out · {user?.name}
        </button>
      </aside>
      <main className="flex-1 p-6">
        <Outlet />
      </main>
    </div>
  );
}
```

`frontend/src/app/provider.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

export function AppProvider({ children }: { children: React.ReactNode }) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
```

`frontend/src/app/router.tsx` — `createRouter(initialEntries?)` using `createMemoryRouter` when entries passed (tests) else `createBrowserRouter`; routes:

```tsx
import { createBrowserRouter, createMemoryRouter, Navigate } from "react-router-dom";
import { AppLayout } from "@/components/layout/app-layout";
import { ProtectedRoute, hasPermission, useUser } from "@/lib/auth";
import { LoginForm } from "@/features/auth/components/login-form";

function HomeRedirect() {
  const { data: user } = useUser();
  if (!user) return null;
  if (!hasPermission(user, "dashboard.view")) return <Navigate to="/my-assignments" replace />;
  return <h1 className="text-xl font-semibold">Dashboard</h1>; // replaced in Stage 6
}

const routes = [
  { path: "/login", element: <LoginForm /> },
  {
    element: <ProtectedRoute />,
    children: [{
      element: <AppLayout />,
      children: [
        { path: "/", element: <HomeRedirect /> },
        { path: "/missions", element: <h1>Missions</h1> },          // Stage 3
        { path: "/crew", element: <h1>Crew</h1> },                  // Stage 2
        { path: "/my-assignments", element: <h1>My Assignments</h1> }, // Stage 4
        { path: "/my-profile", element: <h1>My Profile</h1> },      // Stage 2
        { path: "/settings", element: <h1>Settings</h1> },          // Stage 2
      ],
    }],
  },
];

export function createRouter(initialEntries?: string[]) {
  return initialEntries
    ? createMemoryRouter(routes, { initialEntries })
    : createBrowserRouter(routes);
}
```

`frontend/src/main.tsx` renders `<AppProvider><RouterProvider router={createRouter()} /></AppProvider>`.

- [ ] **Step 3: Verify green + manual smoke**

```bash
npm test -- --run && npm run build
docker compose -f docker-compose.dev.yml up -d
```

Open http://localhost:5173, log in as `lead@helios-aerospace.test` / `orbit-demo-2026` — nav shows Missions but not Settings.

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "feat: login flow, permission-gated app shell and route guards"
```

---

**Stage 1 exit criteria:** `uv run pytest` green · `npm test -- --run` and `npm run build` green · dev compose serves login → shell for all three seeded roles · CI passes on push.
