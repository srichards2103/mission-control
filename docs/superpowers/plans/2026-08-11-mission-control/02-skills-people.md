# Stage 2: Skills & People Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Global constraints in `00-overview.md` apply to every task.

**Goal:** Skill taxonomy + crew proficiency profiles + user management: models with the tenancy-hardening pattern, settings APIs/UI, my-profile editor, crew directory.

**Architecture:** First concrete `TenantModel`s land here, so this stage also proves the scoped-manager and composite-FK guarantees with tests. **Convention set here for all stages:** every API handler's first line is `ensure_permission(request.user, Permission.X)`; object-level rules live in services.

**Tech Stack:** See `00-overview.md`.

---

### Task 2.1: Skill + CrewSkill models with tenancy hardening

**Files:**
- Create: `backend/tests/users/test_tenancy.py`, migrations `users/0002_skill_crewskill.py` (generated) + `users/0003_tenant_composite_fks.py` (hand-written RunSQL)
- Modify: `backend/mission_control/users/models.py`, `backend/mission_control/users/factories.py`

**Interfaces:**
- Produces:
  - `users.models.Skill(TenantModel)`: `name`, `description` (blank ok), `is_archived: bool`; unique `(tenant, lower(name))` named `skill_name_per_tenant_uniq`; `UNIQUE(tenant, id)` named `skill_tenant_id_uniq`
  - `users.models.CrewSkill(TenantModel)`: `user` FK (CASCADE, related_name `crew_skills`), `skill` FK (PROTECT, related_name `crew_skills`), `proficiency` (`1..10` DB check `crewskill_proficiency_1_10`); unique `(user, skill)`
  - `users.factories.SkillFactory`, `users.factories.CrewSkillFactory`
  - DB: composite FKs `(tenant_id, user_id) → users_user(tenant_id, id)` and `(tenant_id, skill_id) → users_skill(tenant_id, id)`

- [ ] **Step 1: Write the failing tests**

`backend/tests/users/test_tenancy.py`:

```python
import pytest
from django.db import IntegrityError

from mission_control.tenants.context import TenantContextNotSet, set_current_tenant_id
from mission_control.users.factories import SkillFactory, TenantFactory, UserFactory
from mission_control.users.models import CrewSkill, Skill

pytestmark = pytest.mark.django_db


def test_scoped_manager_raises_without_context():
    with pytest.raises(TenantContextNotSet):
        list(Skill.objects.all())


def test_scoped_manager_filters_and_stamps():
    t1, t2 = TenantFactory(), TenantFactory()
    SkillFactory(tenant=t2, name="Welding")
    set_current_tenant_id(t1.id)
    skill = Skill(name="Piloting")
    skill.save()  # tenant auto-stamped from context
    assert skill.tenant_id == t1.id
    assert [s.name for s in Skill.objects.all()] == ["Piloting"]


def test_composite_fk_blocks_cross_tenant_link():
    t1, t2 = TenantFactory(), TenantFactory()
    user_t1 = UserFactory(tenant=t1)
    skill_t2 = SkillFactory(tenant=t2)
    with pytest.raises(IntegrityError):
        CrewSkill.objects_unscoped.create(tenant=t2, user=user_t1, skill=skill_t2, proficiency=5)


def test_proficiency_check_constraint():
    user = UserFactory()
    skill = SkillFactory(tenant=user.tenant)
    with pytest.raises(IntegrityError):
        CrewSkill.objects_unscoped.create(tenant=user.tenant, user=user, skill=skill, proficiency=11)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/users/test_tenancy.py -v` — Expected: FAIL (imports missing).

- [ ] **Step 3: Implement models**

Append to `backend/mission_control/users/models.py`:

```python
from django.db.models import Q
from django.db.models.functions import Lower

from mission_control.tenants.models import TenantModel


class Skill(TenantModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_archived = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("name"), "tenant", name="skill_name_per_tenant_uniq"),
            models.UniqueConstraint(fields=["tenant", "id"], name="skill_tenant_id_uniq"),
        ]

    def __str__(self):
        return self.name


class CrewSkill(TenantModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="crew_skills")
    skill = models.ForeignKey(Skill, on_delete=models.PROTECT, related_name="crew_skills")
    proficiency = models.PositiveSmallIntegerField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(proficiency__gte=1) & Q(proficiency__lte=10),
                name="crewskill_proficiency_1_10",
            ),
            models.UniqueConstraint(fields=["user", "skill"], name="crewskill_user_skill_uniq"),
        ]
```

Append factories to `backend/mission_control/users/factories.py`:

```python
from mission_control.users.models import CrewSkill, Skill


class SkillFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Skill

    name = factory.Sequence(lambda n: f"Skill {n}")
    tenant = factory.SubFactory(TenantFactory)


class CrewSkillFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CrewSkill

    user = factory.SubFactory(UserFactory)
    skill = factory.SubFactory(SkillFactory, tenant=factory.SelfAttribute("..user.tenant"))
    tenant = factory.SelfAttribute("user.tenant")
    proficiency = 5
```

- [ ] **Step 4: Generate + hand-write migrations**

```bash
uv run python manage.py makemigrations users
```

Then create `backend/mission_control/users/migrations/0003_tenant_composite_fks.py`:

```python
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [("users", "0002_skill_crewskill")]
    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE users_crewskill
              ADD CONSTRAINT crewskill_tenant_user_fk FOREIGN KEY (tenant_id, user_id)
              REFERENCES users_user (tenant_id, id) DEFERRABLE INITIALLY DEFERRED;
            ALTER TABLE users_crewskill
              ADD CONSTRAINT crewskill_tenant_skill_fk FOREIGN KEY (tenant_id, skill_id)
              REFERENCES users_skill (tenant_id, id) DEFERRABLE INITIALLY DEFERRED;
            """,
            reverse_sql="""
            ALTER TABLE users_crewskill DROP CONSTRAINT crewskill_tenant_user_fk;
            ALTER TABLE users_crewskill DROP CONSTRAINT crewskill_tenant_skill_fk;
            """,
        ),
    ]
```

(If `makemigrations` names 0002 differently, adjust the dependency. This RunSQL pattern is reused for Stage 3/4 join tables.)

- [ ] **Step 5: Run tests to verify they pass, commit**

Run: `uv run pytest tests/users/ -v` — Expected: PASS.

```bash
git add -A && git commit -m "feat: Skill and CrewSkill with tenant scoping and composite-FK hardening"
```

---

### Task 2.2: Skills APIs

**Files:**
- Create: `backend/mission_control/users/services.py`, `backend/mission_control/users/selectors.py`, `backend/mission_control/users/apis/skills.py`, `backend/tests/users/test_skills_api.py`
- Modify: `backend/mission_control/users/urls.py`

**Interfaces:**
- Consumes: `Skill`, `ensure_permission`, `get_paginated_response`
- Produces:
  - `users.services.skill_create(*, actor, name, description="") -> Skill` · `skill_update(*, actor, skill, **fields) -> Skill` (fields: `name`, `description`, `is_archived`; both run `full_clean()` so the lower-name unique surfaces as a 400 envelope)
  - `users.selectors.skill_list() -> QuerySet[Skill]` (ordered by `is_archived`, `name`) · `skill_get(skill_id) -> Skill` (raises `Http404`)
  - `GET /api/v1/skills/` (perm `skill.view`) paginated `{id, name, description, is_archived}` · `POST /api/v1/skills/` (perm `skill.manage`) · `PATCH /api/v1/skills/<id>/` (perm `skill.manage`)

- [ ] **Step 1: Write the failing tests**

`backend/tests/users/test_skills_api.py`:

```python
import pytest

from mission_control.users.factories import SkillFactory, UserFactory
from mission_control.users.roles import Role

pytestmark = pytest.mark.django_db


def test_director_creates_skill(auth_client_for):
    director = UserFactory(role=Role.DIRECTOR)
    client = auth_client_for(director)
    resp = client.post("/api/v1/skills/", {"name": "EVA Ops", "description": "Spacewalks"})
    assert resp.status_code == 201
    assert resp.data["name"] == "EVA Ops"


def test_duplicate_name_case_insensitive_400(auth_client_for):
    director = UserFactory(role=Role.DIRECTOR)
    SkillFactory(tenant=director.tenant, name="Piloting")
    resp = auth_client_for(director).post("/api/v1/skills/", {"name": "piloting"})
    assert resp.status_code == 400
    assert resp.data["message"] == "Validation error"


def test_lead_cannot_manage_but_can_view(auth_client_for):
    lead = UserFactory(role=Role.MISSION_LEAD)
    SkillFactory(tenant=lead.tenant)
    client = auth_client_for(lead)
    assert client.post("/api/v1/skills/", {"name": "X"}).status_code == 403
    assert client.get("/api/v1/skills/").status_code == 200


def test_list_is_tenant_scoped(auth_client_for):
    lead = UserFactory(role=Role.MISSION_LEAD)
    SkillFactory(tenant=lead.tenant, name="Mine")
    SkillFactory(name="Other tenants")  # different tenant via factory default
    resp = auth_client_for(lead).get("/api/v1/skills/")
    assert [s["name"] for s in resp.data["results"]] == ["Mine"]


def test_cross_tenant_patch_is_404(auth_client_for):
    director = UserFactory(role=Role.DIRECTOR)
    other = SkillFactory()  # other tenant
    resp = auth_client_for(director).patch(f"/api/v1/skills/{other.id}/", {"name": "Hijack"})
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/users/test_skills_api.py -v` — Expected: FAIL.

- [ ] **Step 3: Implement**

`backend/mission_control/users/services.py`:

```python
from mission_control.tenants.context import require_current_tenant_id
from mission_control.users.models import Skill


def skill_create(*, actor, name: str, description: str = "") -> Skill:
    # Stamp tenant before full_clean: excluding it would skip the (tenant, lower(name))
    # unique validation and turn duplicate names into 500s instead of 400s.
    skill = Skill(name=name, description=description, tenant_id=require_current_tenant_id())
    skill.full_clean()
    skill.save()
    return skill


def skill_update(*, actor, skill: Skill, **fields) -> Skill:
    for attr in ("name", "description", "is_archived"):
        if attr in fields:
            setattr(skill, attr, fields[attr])
    skill.full_clean()
    skill.save()
    return skill
```

`backend/mission_control/users/selectors.py`:

```python
from django.shortcuts import get_object_or_404

from mission_control.users.models import Skill


def skill_list():
    return Skill.objects.order_by("is_archived", "name")


def skill_get(skill_id: int) -> Skill:
    return get_object_or_404(Skill, id=skill_id)
```

(`get_object_or_404` on the scoped manager makes cross-tenant access a 404 automatically.)

`backend/mission_control/users/apis/skills.py`:

```python
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from mission_control.common.pagination import get_paginated_response
from mission_control.users import selectors, services
from mission_control.users.permissions import Permission, ensure_permission


class SkillOutputSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    description = serializers.CharField()
    is_archived = serializers.BooleanField()


class SkillListCreateApi(APIView):
    class InputSerializer(serializers.Serializer):
        name = serializers.CharField(max_length=100)
        description = serializers.CharField(allow_blank=True, required=False, default="")

    def get(self, request):
        ensure_permission(request.user, Permission.SKILL_VIEW)
        return get_paginated_response(
            serializer_class=SkillOutputSerializer, queryset=selectors.skill_list(), request=request
        )

    def post(self, request):
        ensure_permission(request.user, Permission.SKILL_MANAGE)
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        skill = services.skill_create(actor=request.user, **serializer.validated_data)
        return Response(SkillOutputSerializer(skill).data, status=status.HTTP_201_CREATED)


class SkillUpdateApi(APIView):
    class InputSerializer(serializers.Serializer):
        name = serializers.CharField(max_length=100, required=False)
        description = serializers.CharField(allow_blank=True, required=False)
        is_archived = serializers.BooleanField(required=False)

    def patch(self, request, skill_id: int):
        ensure_permission(request.user, Permission.SKILL_MANAGE)
        skill = selectors.skill_get(skill_id)
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        skill = services.skill_update(actor=request.user, skill=skill, **serializer.validated_data)
        return Response(SkillOutputSerializer(skill).data)
```

Add to `users/urls.py`:

```python
from mission_control.users.apis.skills import SkillListCreateApi, SkillUpdateApi
# ...
    path("skills/", SkillListCreateApi.as_view()),
    path("skills/<int:skill_id>/", SkillUpdateApi.as_view()),
```

- [ ] **Step 4: Run tests to verify they pass, commit**

Run: `uv run pytest tests/users/ -v` — Expected: PASS.

```bash
git add -A && git commit -m "feat: skills list/create/update APIs with tenant-scoped 404s"
```

---

### Task 2.3: My-profile skills API

**Files:**
- Create: `backend/mission_control/users/apis/profile.py`, `backend/tests/users/test_profile_api.py`
- Modify: `backend/mission_control/users/services.py`, `backend/mission_control/users/selectors.py`, `backend/mission_control/users/urls.py`

**Interfaces:**
- Produces:
  - `users.services.crew_skills_set(*, actor, items: list[dict]) -> None` — items `[{"skill_id": int, "proficiency": int}]`; replaces the actor's full profile; raises `ApplicationError` for unknown/archived skills or duplicate skill_ids
  - `users.selectors.crew_skills_for_user(user) -> QuerySet[CrewSkill]` (select_related skill, ordered by skill name)
  - `GET·PUT /api/v1/me/skills/` (perm `own_skills.edit`) — rows `{skill_id, skill_name, proficiency}`

- [ ] **Step 1: Write the failing tests**

`backend/tests/users/test_profile_api.py`:

```python
import pytest

from mission_control.users.factories import CrewSkillFactory, SkillFactory, UserFactory
from mission_control.users.models import CrewSkill
from mission_control.users.roles import Role

pytestmark = pytest.mark.django_db


def test_put_replaces_profile(auth_client_for):
    crew = UserFactory(role=Role.CREW_MEMBER)
    old = CrewSkillFactory(user=crew)
    s1, s2 = SkillFactory(tenant=crew.tenant), SkillFactory(tenant=crew.tenant)
    client = auth_client_for(crew)
    resp = client.put("/api/v1/me/skills/", {"items": [
        {"skill_id": s1.id, "proficiency": 7}, {"skill_id": s2.id, "proficiency": 3},
    ]}, format="json")
    assert resp.status_code == 200
    rows = CrewSkill.objects_unscoped.filter(user=crew)
    assert {(r.skill_id, r.proficiency) for r in rows} == {(s1.id, 7), (s2.id, 3)}
    assert not rows.filter(skill=old.skill).exists()


def test_archived_skill_rejected(auth_client_for):
    crew = UserFactory(role=Role.CREW_MEMBER)
    archived = SkillFactory(tenant=crew.tenant, is_archived=True)
    resp = auth_client_for(crew).put("/api/v1/me/skills/",
        {"items": [{"skill_id": archived.id, "proficiency": 5}]}, format="json")
    assert resp.status_code == 400


def test_out_of_range_proficiency_rejected(auth_client_for):
    crew = UserFactory(role=Role.CREW_MEMBER)
    skill = SkillFactory(tenant=crew.tenant)
    resp = auth_client_for(crew).put("/api/v1/me/skills/",
        {"items": [{"skill_id": skill.id, "proficiency": 11}]}, format="json")
    assert resp.status_code == 400


def test_directors_cannot_edit_profile(auth_client_for):
    director = UserFactory(role=Role.DIRECTOR)
    resp = auth_client_for(director).put("/api/v1/me/skills/", {"items": []}, format="json")
    assert resp.status_code == 403
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/users/test_profile_api.py -v` — Expected: FAIL.

- [ ] **Step 3: Implement**

Append to `users/services.py`:

```python
from django.db import transaction

from mission_control.common.exceptions import ApplicationError
from mission_control.tenants.context import require_current_tenant_id
from mission_control.users.models import CrewSkill


@transaction.atomic
def crew_skills_set(*, actor, items: list[dict]) -> None:
    skill_ids = [item["skill_id"] for item in items]
    if len(skill_ids) != len(set(skill_ids)):
        raise ApplicationError("Duplicate skills in profile.")
    valid_ids = set(
        Skill.objects.filter(id__in=skill_ids, is_archived=False).values_list("id", flat=True)
    )
    missing = set(skill_ids) - valid_ids
    if missing:
        raise ApplicationError("Unknown or archived skills.", extra={"skill_ids": sorted(missing)})
    CrewSkill.objects.filter(user=actor).delete()
    CrewSkill.objects_unscoped.bulk_create([
        CrewSkill(tenant_id=require_current_tenant_id(), user=actor,
                  skill_id=item["skill_id"], proficiency=item["proficiency"])
        for item in items
    ])
```

Append to `users/selectors.py`:

```python
from mission_control.users.models import CrewSkill


def crew_skills_for_user(user):
    return CrewSkill.objects.filter(user=user).select_related("skill").order_by("skill__name")
```

`backend/mission_control/users/apis/profile.py`:

```python
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from mission_control.users import selectors, services
from mission_control.users.permissions import Permission, ensure_permission


class MySkillsApi(APIView):
    class ItemSerializer(serializers.Serializer):
        skill_id = serializers.IntegerField()
        proficiency = serializers.IntegerField(min_value=1, max_value=10)

    class InputSerializer(serializers.Serializer):
        items = serializers.ListField(child=serializers.DictField())

    class OutputSerializer(serializers.Serializer):
        skill_id = serializers.IntegerField()
        skill_name = serializers.CharField(source="skill.name")
        proficiency = serializers.IntegerField()

    def get(self, request):
        ensure_permission(request.user, Permission.OWN_SKILLS_EDIT)
        rows = selectors.crew_skills_for_user(request.user)
        return Response({"items": self.OutputSerializer(rows, many=True).data})

    def put(self, request):
        ensure_permission(request.user, Permission.OWN_SKILLS_EDIT)
        items_serializer = self.ItemSerializer(data=request.data.get("items", []), many=True)
        items_serializer.is_valid(raise_exception=True)
        services.crew_skills_set(actor=request.user, items=items_serializer.validated_data)
        rows = selectors.crew_skills_for_user(request.user)
        return Response({"items": self.OutputSerializer(rows, many=True).data})
```

Add to `users/urls.py`: `path("me/skills/", MySkillsApi.as_view())`.

- [ ] **Step 4: Run tests to verify they pass, commit**

Run: `uv run pytest tests/users/ -v` — Expected: PASS.

```bash
git add -A && git commit -m "feat: own skill profile bulk upsert API"
```

---

### Task 2.4: Crew directory APIs

**Files:**
- Create: `backend/mission_control/users/apis/crew.py`, `backend/tests/users/test_crew_api.py`
- Modify: `backend/mission_control/users/selectors.py`, `backend/mission_control/users/urls.py`

**Interfaces:**
- Produces:
  - `users.selectors.crew_list() -> QuerySet[User]` — active `CREW_MEMBER`s of the current tenant, `prefetch_related("crew_skills__skill")`, ordered by name. **Explicitly filters `tenant_id=require_current_tenant_id()`** (User has a standard manager). · `crew_get(user_id) -> User` (404 outside tenant/role)
  - `GET /api/v1/crew/` (perm `crew.view`) paginated `{id, name, email, skills: [{skill_id, name, proficiency}]}` · `GET /api/v1/crew/<id>/` (same shape)

- [ ] **Step 1: Write the failing tests**

`backend/tests/users/test_crew_api.py`:

```python
import pytest

from mission_control.users.factories import CrewSkillFactory, UserFactory
from mission_control.users.roles import Role

pytestmark = pytest.mark.django_db


def test_crew_list_scoped_with_skills(auth_client_for):
    lead = UserFactory(role=Role.MISSION_LEAD)
    crew = UserFactory(role=Role.CREW_MEMBER, tenant=lead.tenant, name="Ada")
    CrewSkillFactory(user=crew, proficiency=8)
    UserFactory(role=Role.CREW_MEMBER)  # other tenant
    UserFactory(role=Role.DIRECTOR, tenant=lead.tenant)  # not crew
    resp = auth_client_for(lead).get("/api/v1/crew/")
    assert resp.status_code == 200
    assert [c["name"] for c in resp.data["results"]] == ["Ada"]
    assert resp.data["results"][0]["skills"][0]["proficiency"] == 8


def test_crew_member_cannot_view_directory(auth_client_for):
    crew = UserFactory(role=Role.CREW_MEMBER)
    assert auth_client_for(crew).get("/api/v1/crew/").status_code == 403


def test_cross_tenant_detail_404(auth_client_for):
    lead = UserFactory(role=Role.MISSION_LEAD)
    other = UserFactory(role=Role.CREW_MEMBER)  # other tenant
    assert auth_client_for(lead).get(f"/api/v1/crew/{other.id}/").status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/users/test_crew_api.py -v` — Expected: FAIL.

- [ ] **Step 3: Implement**

Append to `users/selectors.py`:

```python
from django.shortcuts import get_object_or_404 as _get_object_or_404

from mission_control.tenants.context import require_current_tenant_id
from mission_control.users.models import User
from mission_control.users.roles import Role


def crew_list():
    return (
        User.objects.filter(tenant_id=require_current_tenant_id(), role=Role.CREW_MEMBER, is_active=True)
        .prefetch_related("crew_skills__skill")
        .order_by("name")
    )


def crew_get(user_id: int) -> User:
    return _get_object_or_404(crew_list(), id=user_id)
```

`backend/mission_control/users/apis/crew.py`:

```python
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from mission_control.common.pagination import get_paginated_response
from mission_control.users import selectors
from mission_control.users.permissions import Permission, ensure_permission


class CrewOutputSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    email = serializers.EmailField()
    skills = serializers.SerializerMethodField()

    def get_skills(self, user):
        return [
            {"skill_id": cs.skill_id, "name": cs.skill.name, "proficiency": cs.proficiency}
            for cs in user.crew_skills.all()
        ]


class CrewListApi(APIView):
    def get(self, request):
        ensure_permission(request.user, Permission.CREW_VIEW)
        return get_paginated_response(
            serializer_class=CrewOutputSerializer, queryset=selectors.crew_list(), request=request
        )


class CrewDetailApi(APIView):
    def get(self, request, user_id: int):
        ensure_permission(request.user, Permission.CREW_VIEW)
        return Response(CrewOutputSerializer(selectors.crew_get(user_id)).data)
```

Add to `users/urls.py`: `path("crew/", CrewListApi.as_view())`, `path("crew/<int:user_id>/", CrewDetailApi.as_view())`.

- [ ] **Step 4: Run tests to verify they pass, commit**

Run: `uv run pytest tests/users/ -v` — Expected: PASS.

```bash
git add -A && git commit -m "feat: crew directory APIs"
```

---

### Task 2.5: Settings APIs — users + organisation

**Files:**
- Create: `backend/mission_control/users/apis/settings.py`, `backend/mission_control/tenants/services.py`, `backend/tests/users/test_settings_api.py`
- Modify: `backend/mission_control/users/services.py`, `backend/mission_control/users/selectors.py`, `backend/mission_control/users/urls.py`

**Interfaces:**
- Produces:
  - `users.services.user_create(*, actor, email, name, role, password) -> User` (raises `ApplicationError` on duplicate email) · `user_update(*, actor, user, role=None, is_active=None) -> User` (raises `ApplicationError("You cannot change your own account.")` when `user == actor`)
  - `users.selectors.user_list() -> QuerySet[User]` (all roles, current tenant, ordered by name) · `user_get(user_id)` (tenant-scoped 404)
  - `tenants.services.tenant_update(*, actor, tenant, name) -> Tenant`
  - `GET·POST /api/v1/settings/users/` (perm `user.manage`) `{id, name, email, role, is_active}` · `PATCH /api/v1/settings/users/<id>/` (`role`, `is_active`)
  - `GET /api/v1/settings/organisation/` (perm `settings.view`) `{id, name, slug}` · `PATCH` (perm `settings.manage`) `{name}`

- [ ] **Step 1: Write the failing tests**

`backend/tests/users/test_settings_api.py`:

```python
import pytest

from mission_control.users.factories import UserFactory
from mission_control.users.models import User
from mission_control.users.roles import Role

pytestmark = pytest.mark.django_db


def test_director_creates_user(auth_client_for):
    director = UserFactory(role=Role.DIRECTOR)
    resp = auth_client_for(director).post("/api/v1/settings/users/", {
        "email": "new@example.com", "name": "New Crew", "role": "crew_member", "password": "s3cret-pw",
    })
    assert resp.status_code == 201
    created = User.objects.get(email="new@example.com")
    assert created.tenant_id == director.tenant_id
    assert created.check_password("s3cret-pw")


def test_lead_cannot_manage_users(auth_client_for):
    lead = UserFactory(role=Role.MISSION_LEAD)
    assert auth_client_for(lead).get("/api/v1/settings/users/").status_code == 403


def test_deactivate_and_role_change(auth_client_for):
    director = UserFactory(role=Role.DIRECTOR)
    crew = UserFactory(role=Role.CREW_MEMBER, tenant=director.tenant)
    resp = auth_client_for(director).patch(f"/api/v1/settings/users/{crew.id}/",
                                           {"role": "mission_lead", "is_active": False})
    assert resp.status_code == 200
    crew.refresh_from_db()
    assert crew.role == Role.MISSION_LEAD and crew.is_active is False


def test_cannot_change_own_account(auth_client_for):
    director = UserFactory(role=Role.DIRECTOR)
    resp = auth_client_for(director).patch(f"/api/v1/settings/users/{director.id}/", {"is_active": False})
    assert resp.status_code == 400


def test_organisation_rename(auth_client_for):
    director = UserFactory(role=Role.DIRECTOR)
    resp = auth_client_for(director).patch("/api/v1/settings/organisation/", {"name": "Helios Renamed"})
    assert resp.status_code == 200
    director.tenant.refresh_from_db()
    assert director.tenant.name == "Helios Renamed"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/users/test_settings_api.py -v` — Expected: FAIL.

- [ ] **Step 3: Implement**

Append to `users/services.py`:

```python
from mission_control.users.models import User
from mission_control.users.roles import Role


def user_create(*, actor, email: str, name: str, role: str, password: str) -> User:
    if User.objects.filter(email__iexact=email).exists():
        raise ApplicationError("A user with this email already exists.")
    return User.objects.create_user(
        email=email, password=password, tenant=actor.tenant, role=role, name=name
    )


def user_update(*, actor, user: User, role: str | None = None, is_active: bool | None = None) -> User:
    if user == actor:
        raise ApplicationError("You cannot change your own account.")
    if role is not None:
        user.role = role
    if is_active is not None:
        user.is_active = is_active
    user.save()
    return user
```

Append to `users/selectors.py`:

```python
def user_list():
    return User.objects.filter(tenant_id=require_current_tenant_id()).order_by("name")


def user_get(user_id: int) -> User:
    return _get_object_or_404(user_list(), id=user_id)
```

`backend/mission_control/tenants/services.py`:

```python
from mission_control.tenants.models import Tenant


def tenant_update(*, actor, tenant: Tenant, name: str) -> Tenant:
    tenant.name = name
    tenant.full_clean()
    tenant.save()
    return tenant
```

`backend/mission_control/users/apis/settings.py` — three `APIView`s in the established pattern:

- `SettingsUserListCreateApi` — `get` (`user.manage`): paginated `user_list()` with inline output serializer `{id, name, email, role, is_active}`; `post` (`user.manage`): inline input `{email, name, role: ChoiceField(Role.choices), password: CharField(min_length=8)}` → `services.user_create` → 201.
- `SettingsUserUpdateApi.patch` (`user.manage`): input `{role?, is_active?}` → `selectors.user_get` → `services.user_update`.
- `OrganisationApi` — `get` (`settings.view`): `{id, name, slug}` from `request.user.tenant`; `patch` (`settings.manage`): `{name: CharField(max_length=255)}` → `tenants.services.tenant_update`.

Add to `users/urls.py`: `settings/users/`, `settings/users/<int:user_id>/`, `settings/organisation/`.

- [ ] **Step 4: Run tests to verify they pass, commit**

Run: `uv run pytest tests/ -v` — Expected: PASS.

```bash
git add -A && git commit -m "feat: settings APIs for user management and organisation"
```

---

### Task 2.6: Frontend — settings area

**Files:**
- Create: `frontend/src/features/skills/api/skills.ts`, `frontend/src/features/settings/api/settings.ts`, `frontend/src/features/settings/components/{settings-page.tsx,users-tab.tsx,skills-tab.tsx,organisation-tab.tsx}`, `frontend/src/features/settings/settings.test.tsx`
- Modify: `frontend/src/app/router.tsx` (replace `/settings` placeholder), `frontend/src/testing/mocks.ts` (add handlers + `directorUser`)

**Interfaces:**
- Consumes: `api`, zod, `RequirePermission`, shadcn `Tabs/Table/Dialog/Input/Button/Badge/Select`
- Produces:
  - `features/skills/api/skills.ts`: `SkillSchema` `{id, name, description, is_archived}`, `useSkills()` (key `["skills"]`, parses `PaginatedSchema(SkillSchema)`), `useCreateSkill()`, `useUpdateSkill()` (invalidate `["skills"]`). Also exports the generic `PaginatedSchema(item)` zod helper `{results, count, limit, offset}` — **defined once here, reused by every later feature**.
  - `features/settings/api/settings.ts`: `OrgUserSchema`, `useOrgUsers`, `useCreateUser`, `useUpdateUser`, `OrganisationSchema`, `useOrganisation`, `useUpdateOrganisation`
  - `/settings` route: `<RequirePermission permission="settings.view">` wrapping tabs — Users (table: name/email/role badge/active + "Add user" dialog + row actions change-role/deactivate), Skills (table with inline add row + inline edit + archive toggle), Organisation (name shown, inline editable — click to input + save)

- [ ] **Step 1: Write the failing tests**

`frontend/src/features/settings/settings.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { RouterProvider } from "react-router-dom";
import { AppProvider } from "@/app/provider";
import { createRouter } from "@/app/router";
import { crewUser, directorUser, server } from "@/testing/mocks";

function renderAt(path: string) {
  render(<AppProvider><RouterProvider router={createRouter([path])} /></AppProvider>);
}

describe("settings", () => {
  it("crew member is bounced away from settings", async () => {
    server.use(http.get("/api/v1/auth/me/", () => HttpResponse.json(crewUser)));
    renderAt("/settings");
    expect(await screen.findByRole("heading", { name: /my assignments/i })).toBeInTheDocument();
  });

  it("director sees tabs and creates a skill", async () => {
    server.use(http.get("/api/v1/auth/me/", () => HttpResponse.json(directorUser)));
    renderAt("/settings");
    await userEvent.click(await screen.findByRole("tab", { name: /skills/i }));
    expect(await screen.findByText("Piloting")).toBeInTheDocument();
    await userEvent.type(screen.getByPlaceholderText(/new skill name/i), "EVA Ops");
    await userEvent.click(screen.getByRole("button", { name: /add skill/i }));
    expect(await screen.findByText("EVA Ops")).toBeInTheDocument();
  });
});
```

Add to `mocks.ts`: `directorUser` (14 director permissions incl. `settings.view`, `settings.manage`, `user.manage`, `skill.manage`), plus handlers:

```ts
const skills = [{ id: 1, name: "Piloting", description: "", is_archived: false }];
http.get("/api/v1/skills/", () =>
  HttpResponse.json({ results: skills, count: skills.length, limit: 25, offset: 0 })),
http.post("/api/v1/skills/", async ({ request }) => {
  const body = (await request.json()) as { name: string };
  const skill = { id: skills.length + 1, name: body.name, description: "", is_archived: false };
  skills.push(skill);
  return HttpResponse.json(skill, { status: 201 });
}),
http.get("/api/v1/settings/users/", () =>
  HttpResponse.json({ results: [directorUser], count: 1, limit: 25, offset: 0 })),
http.get("/api/v1/settings/organisation/", () =>
  HttpResponse.json({ id: 1, name: "Helios", slug: "helios" })),
```

Run: `npm test -- --run` — Expected: FAIL.

- [ ] **Step 2: Implement**

`frontend/src/features/skills/api/skills.ts`:

```ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { api } from "@/lib/api-client";

export const PaginatedSchema = <T extends z.ZodTypeAny>(item: T) =>
  z.object({ results: z.array(item), count: z.number(), limit: z.number(), offset: z.number() });

export const SkillSchema = z.object({
  id: z.number(), name: z.string(), description: z.string(), is_archived: z.boolean(),
});
export type Skill = z.infer<typeof SkillSchema>;

export function useSkills() {
  return useQuery({
    queryKey: ["skills"],
    queryFn: async () => PaginatedSchema(SkillSchema).parse((await api.get("/skills/", { params: { limit: 100 } })).data).results,
  });
}

export function useCreateSkill() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { name: string; description?: string }) =>
      SkillSchema.parse((await api.post("/skills/", input)).data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["skills"] }),
  });
}

export function useUpdateSkill() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...patch }: { id: number } & Partial<Skill>) =>
      SkillSchema.parse((await api.patch(`/skills/${id}/`, patch)).data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["skills"] }),
  });
}
```

`features/settings/api/settings.ts` — same pattern: `OrgUserSchema` `{id, name, email, role, is_active}`, `useOrgUsers` (key `["settings","users"]`), `useCreateUser` (POST `{email,name,role,password}`), `useUpdateUser` (PATCH), `OrganisationSchema` `{id,name,slug}`, `useOrganisation` (key `["settings","organisation"]`), `useUpdateOrganisation` (PATCH `{name}`).

Components:
- `settings-page.tsx`: `<h1>Settings</h1>` + shadcn `Tabs` (`users` default) with the three tab components.
- `users-tab.tsx`: table of users (role as `Badge`, inactive rows muted); "Add user" `Dialog` (email/name/password inputs + role `Select`); per-row role `Select` (calls `useUpdateUser`) and Deactivate/Reactivate button.
- `skills-tab.tsx`: table with rows (name, description, archived badge, Archive/Restore button via `useUpdateSkill`), plus a persistent bottom row: inputs with placeholders "New skill name" / "Description" and an "Add skill" button (`useCreateSkill`). Mutation errors surface via `toast.error(err.response?.data?.message)`.
- `organisation-tab.tsx`: org name — read view with pencil icon; click swaps to input + Save (inline-edit pattern).

Router: replace the `/settings` placeholder with

```tsx
{ path: "/settings", element: (
  <RequirePermission permission="settings.view"><SettingsPage /></RequirePermission>
) },
```

- [ ] **Step 3: Verify green, commit**

Run: `npm test -- --run && npm run build` — Expected: PASS.

```bash
git add -A && git commit -m "feat: settings area with users, skills, organisation tabs"
```

---

### Task 2.7: Frontend — my-profile editor + crew directory

**Files:**
- Create: `frontend/src/features/profile/api/profile.ts`, `frontend/src/features/profile/components/profile-page.tsx`, `frontend/src/features/crew/api/crew.ts`, `frontend/src/features/crew/components/{crew-list-page.tsx,crew-detail-page.tsx}`, `frontend/src/features/profile/profile.test.tsx`
- Modify: `frontend/src/app/router.tsx` (replace `/my-profile`, `/crew` placeholders; add `/crew/:crewId`), `frontend/src/testing/mocks.ts`

**Interfaces:**
- Produces:
  - `features/profile/api/profile.ts`: `MySkillSchema` `{skill_id, skill_name, proficiency}`, `useMySkills()` (key `["me","skills"]`, GET returns `{items}`), `useSetMySkills()` (PUT `{items: [{skill_id, proficiency}]}`, invalidates)
  - `features/crew/api/crew.ts`: `CrewMemberSchema` `{id, name, email, skills: [{skill_id, name, proficiency}]}`, `useCrew()` (key `["crew"]`), `useCrewMember(id)`
  - `/my-profile`: gated `own_skills.edit` — profile rows (skill name + proficiency `Select` 1–10 + remove); "Add skill" row (Select of non-archived skills not yet chosen); Save calls `useSetMySkills`
  - `/crew` gated `crew.view`: table (name, email, skills as `Badge`s "Piloting 8") linking to `/crew/:crewId` detail card

- [ ] **Step 1: Write the failing test**

`frontend/src/features/profile/profile.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { RouterProvider } from "react-router-dom";
import { AppProvider } from "@/app/provider";
import { createRouter } from "@/app/router";
import { crewUser, server } from "@/testing/mocks";

it("crew member edits and saves their profile", async () => {
  server.use(http.get("/api/v1/auth/me/", () => HttpResponse.json(crewUser)));
  let putBody: unknown = null;
  server.use(http.put("/api/v1/me/skills/", async ({ request }) => {
    putBody = await request.json();
    return HttpResponse.json({ items: [{ skill_id: 1, skill_name: "Piloting", proficiency: 9 }] });
  }));
  render(<AppProvider><RouterProvider router={createRouter(["/my-profile"])} /></AppProvider>);
  expect(await screen.findByText("Piloting")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /save/i }));
  expect(putBody).toEqual({ items: [{ skill_id: 1, proficiency: 8 }] });
});
```

Add handlers to `mocks.ts`: `GET /api/v1/me/skills/` → `{items: [{skill_id: 1, skill_name: "Piloting", proficiency: 8}]}`, `GET /api/v1/crew/` → paginated one member.

Run: `npm test -- --run` — Expected: FAIL.

- [ ] **Step 2: Implement** the api modules and components per the Interfaces block. Profile page keeps a local draft state initialised from `useMySkills`, mutates on Save, `toast.success("Profile saved")` on success. Crew pages are read-only tables/cards in the Task 2.6 idiom. Router swaps in the real pages with `RequirePermission` (`own_skills.edit` / `crew.view`).

- [ ] **Step 3: Verify green + manual smoke, commit**

```bash
npm test -- --run && npm run build
```

Manual: log in as `crew1@helios-aerospace.test` → edit profile; as lead → browse crew.

```bash
git add -A && git commit -m "feat: my-profile skills editor and crew directory"
```

---

**Stage 2 exit criteria:** backend + frontend suites green · director can curate skills/users/org name · crew member can maintain their profile · lead can browse the crew directory · all list endpoints proven tenant-scoped by tests.
