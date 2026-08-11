# Stage 3: Missions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Global constraints in `00-overview.md` apply to every task.

**Goal:** Mission domain: models (Mission, MissionTransition, MissionRequirement), the seven-state FSM service with per-transition permissions, mission CRUD + lifecycle APIs, and the missions UI (list, create, detail, requirements editor, transitions, history).

**Architecture:** The FSM is a data table; `transition_mission` is the only status writer. Stage-3 `approve` enforces self-approval + state only — Stage 4 Task 4.4 adds the staffing guard; Stage 4 also extends `cancel` to flip live assignments (assignments don't exist yet).

**Tech Stack:** See `00-overview.md`.

---

### Task 3.1: Mission models

**Files:**
- Create: `backend/mission_control/missions/{__init__.py,apps.py,models.py,factories.py,urls.py}`, migrations `missions/0001_initial.py` (generated) + `missions/0002_tenant_composite_fks.py`, `backend/tests/missions/{__init__.py,test_models.py}`
- Modify: `backend/config/settings.py` (add `mission_control.missions` to INSTALLED_APPS), `backend/config/urls.py` (include `mission_control.missions.urls`)

**Interfaces:**
- Produces:
  - `missions.models.MissionStatus` (TextChoices): `DRAFT="draft"`, `PENDING_APPROVAL="pending_approval"`, `APPROVED="approved"`, `REJECTED="rejected"`, `ACTIVE="active"`, `COMPLETED="completed"`, `CANCELLED="cancelled"`
  - `missions.models.Mission(TenantModel)`: `name`, `description` (blank ok), `start_date`, `end_date`, `status` (default DRAFT), `min_crew` (PositiveSmallIntegerField), `max_crew`, `created_by` FK(User, PROTECT, related_name `created_missions`). DB checks: `mission_dates_ordered` (`end_date >= start_date`), `mission_crew_bounds` (`min_crew >= 1 AND max_crew >= min_crew`); `UNIQUE(tenant, id)` named `mission_tenant_id_uniq`
  - `missions.models.MissionTransition(TenantModel)`: `mission` FK (CASCADE, related_name `transitions`), `from_status`, `to_status`, `actor` FK(User, PROTECT, related_name `+`), `reason` (blank ok)
  - `missions.models.MissionRequirement(TenantModel)`: `mission` FK (CASCADE, related_name `requirements`), `skill` FK (PROTECT, related_name `+`), `min_proficiency` (check `1..10` named `requirement_proficiency_1_10`), `required_count` (check `>= 1` named `requirement_count_gte_1`); unique `(mission, skill, min_proficiency)` named `requirement_mission_skill_prof_uniq`
  - Composite FKs (0002, same RunSQL pattern as Stage 2 Task 2.1): `missions_missionrequirement (tenant_id, mission_id) → missions_mission (tenant_id, id)` and `(tenant_id, skill_id) → users_skill (tenant_id, id)`
  - `missions.factories.MissionFactory` (tenant, created_by = lead of same tenant, dates today+10 → today+20, `min_crew=1`, `max_crew=3`), `missions.factories.MissionRequirementFactory` (mission SubFactory, skill same tenant, `min_proficiency=5`, `required_count=1`)
- Consumes: `TenantModel`, `User`, `Skill`

- [ ] **Step 1: Write the failing tests**

`backend/tests/missions/test_models.py`:

```python
import datetime as dt

import pytest
from django.db import IntegrityError

from mission_control.missions.factories import MissionFactory
from mission_control.missions.models import Mission, MissionStatus

pytestmark = pytest.mark.django_db

TODAY = dt.date(2026, 8, 11)


def test_defaults_to_draft():
    assert MissionFactory().status == MissionStatus.DRAFT


def test_dates_must_be_ordered():
    with pytest.raises(IntegrityError):
        MissionFactory(start_date=TODAY, end_date=TODAY - dt.timedelta(days=1))


def test_crew_bounds_check():
    with pytest.raises(IntegrityError):
        MissionFactory(min_crew=5, max_crew=2)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/missions/ -v` — Expected: FAIL (module missing).

- [ ] **Step 3: Implement**

`backend/mission_control/missions/models.py`:

```python
from django.db import models
from django.db.models import F, Q

from mission_control.tenants.models import TenantModel
from mission_control.users.models import Skill, User


class MissionStatus(models.TextChoices):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Mission(TenantModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=32, choices=MissionStatus.choices, default=MissionStatus.DRAFT)
    min_crew = models.PositiveSmallIntegerField()
    max_crew = models.PositiveSmallIntegerField()
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="created_missions")

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(end_date__gte=F("start_date")), name="mission_dates_ordered"),
            models.CheckConstraint(condition=Q(min_crew__gte=1) & Q(max_crew__gte=F("min_crew")),
                                   name="mission_crew_bounds"),
            models.UniqueConstraint(fields=["tenant", "id"], name="mission_tenant_id_uniq"),
        ]

    def __str__(self):
        return self.name


class MissionTransition(TenantModel):
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name="transitions")
    from_status = models.CharField(max_length=32, choices=MissionStatus.choices)
    to_status = models.CharField(max_length=32, choices=MissionStatus.choices)
    actor = models.ForeignKey(User, on_delete=models.PROTECT, related_name="+")
    reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]


class MissionRequirement(TenantModel):
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name="requirements")
    skill = models.ForeignKey(Skill, on_delete=models.PROTECT, related_name="+")
    min_proficiency = models.PositiveSmallIntegerField()
    required_count = models.PositiveSmallIntegerField(default=1)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(min_proficiency__gte=1) & Q(min_proficiency__lte=10),
                                   name="requirement_proficiency_1_10"),
            models.CheckConstraint(condition=Q(required_count__gte=1), name="requirement_count_gte_1"),
            models.UniqueConstraint(fields=["mission", "skill", "min_proficiency"],
                                    name="requirement_mission_skill_prof_uniq"),
        ]
```

`missions/apps.py`, `missions/urls.py` (empty `urlpatterns = []` for now), factories:

`backend/mission_control/missions/factories.py`:

```python
import datetime as dt

import factory

from mission_control.missions.models import Mission, MissionRequirement
from mission_control.users.factories import SkillFactory, TenantFactory, UserFactory
from mission_control.users.roles import Role


class MissionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Mission

    tenant = factory.SubFactory(TenantFactory)
    name = factory.Sequence(lambda n: f"Mission {n}")
    # Relative dates: tests that rely on "starts in the future" (activate guard) stay valid forever.
    start_date = factory.LazyFunction(lambda: dt.date.today() + dt.timedelta(days=10))
    end_date = factory.LazyFunction(lambda: dt.date.today() + dt.timedelta(days=20))
    min_crew = 1
    max_crew = 3
    created_by = factory.SubFactory(
        UserFactory, role=Role.MISSION_LEAD, tenant=factory.SelfAttribute("..tenant")
    )


class MissionRequirementFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MissionRequirement

    mission = factory.SubFactory(MissionFactory)
    tenant = factory.SelfAttribute("mission.tenant")
    skill = factory.SubFactory(SkillFactory, tenant=factory.SelfAttribute("..mission.tenant"))
    min_proficiency = 5
    required_count = 1
```

Settings: add `"mission_control.missions"` to INSTALLED_APPS; `config/urls.py` → `path("api/v1/", include("mission_control.missions.urls"))` alongside the users include.

- [ ] **Step 4: Migrations (incl. composite FKs), tests, commit**

```bash
uv run python manage.py makemigrations missions
# then write missions/migrations/0002_tenant_composite_fks.py (RunSQL per Interfaces block)
uv run pytest tests/ -v
git add -A && git commit -m "feat: Mission, MissionTransition, MissionRequirement models"
```

---

### Task 3.2: FSM service + mission services

**Files:**
- Create: `backend/mission_control/missions/services/{__init__.py,missions.py}`, `backend/mission_control/missions/selectors/{__init__.py,missions.py}`, `backend/tests/missions/test_fsm.py`, `backend/tests/missions/test_mission_services.py`

**Interfaces:**
- Produces (`missions.services.missions`):
  - `TRANSITIONS: dict[str, Transition]` — `Transition(from_statuses: frozenset, to_status: str, permission: Permission, requires_reason: bool)`; actions: `submit, approve, reject, revise, activate, complete, cancel` exactly per spec §8
  - `transition_mission(*, actor, mission, action, reason=None) -> Mission` — atomic; `select_for_update` on the mission; order of checks: **action known → permission (from table) → ownership (progress actions: lead must own; directors any) → self-review block (approve/reject) → state validity → reason present if required → domain guards** → write status + `MissionTransition`
  - `mission_create(*, actor, name, description, start_date, end_date, min_crew, max_crew) -> Mission` (full_clean incl. tenant-excluded, so check-constraint violations surface as 400 not 500)
  - `mission_update(*, actor, mission, **fields) -> Mission` — only DRAFT/REJECTED else `ApplicationError("Mission can only be edited in draft or rejected state.")`; ownership rule
  - `mission_requirements_set(*, actor, mission, items: list[dict]) -> None` — items `[{skill_id, min_proficiency, required_count}]`; only DRAFT/REJECTED; ownership; validates skills exist, not archived, no duplicate `(skill_id, min_proficiency)` pairs
- Produces (`missions.selectors.missions`):
  - `mission_list(*, status=None, search=None) -> QuerySet[Mission]` (newest first; `search` = icontains on name)
  - `mission_get(mission_id) -> Mission` (prefetch `requirements__skill`, `transitions__actor`; tenant-scoped 404)
  - `mission_submitter_id(mission) -> int | None` (actor of latest transition into PENDING_APPROVAL)
- Guard notes: `submit` requires ≥1 requirement; `activate` requires `start_date <= date.today()`; `complete` requires `end_date <= date.today()`; `cancel` from any non-terminal (not COMPLETED/CANCELLED). Stage 4 replaces the `approve` staffing no-op (`_validate_staffing_for_approval(mission)`, defined here returning `None`) with the real check — define the hook function now so Stage 4 only edits one function body.

- [ ] **Step 1: Write the failing tests**

`backend/tests/missions/test_fsm.py`:

```python
import datetime as dt

import pytest
from rest_framework.exceptions import PermissionDenied

from mission_control.common.exceptions import ApplicationError
from mission_control.missions.factories import MissionFactory, MissionRequirementFactory
from mission_control.missions.models import MissionStatus
from mission_control.missions.services.missions import transition_mission
from mission_control.tenants.context import set_current_tenant_id
from mission_control.users.factories import UserFactory
from mission_control.users.roles import Role

pytestmark = pytest.mark.django_db


@pytest.fixture
def mission_with_requirement():
    mission = MissionFactory()
    MissionRequirementFactory(mission=mission)
    set_current_tenant_id(mission.tenant_id)
    return mission


def director_for(mission):
    return UserFactory(role=Role.DIRECTOR, tenant=mission.tenant)


def test_happy_path_submit_approve(mission_with_requirement):
    mission = mission_with_requirement
    lead = mission.created_by
    mission = transition_mission(actor=lead, mission=mission, action="submit")
    assert mission.status == MissionStatus.PENDING_APPROVAL
    mission = transition_mission(actor=director_for(mission), mission=mission, action="approve")
    assert mission.status == MissionStatus.APPROVED
    assert mission.transitions.count() == 2


def test_submit_requires_a_requirement():
    mission = MissionFactory()
    set_current_tenant_id(mission.tenant_id)
    with pytest.raises(ApplicationError, match="requirement"):
        transition_mission(actor=mission.created_by, mission=mission, action="submit")


def test_creator_director_cannot_approve_own():
    director = UserFactory(role=Role.DIRECTOR)
    mission = MissionFactory(tenant=director.tenant, created_by=director)
    MissionRequirementFactory(mission=mission)
    set_current_tenant_id(mission.tenant_id)
    transition_mission(actor=director, mission=mission, action="submit")
    with pytest.raises(PermissionDenied):
        transition_mission(actor=director, mission=mission, action="approve")


def test_submitter_cannot_approve(mission_with_requirement):
    mission = mission_with_requirement
    submitting_director = director_for(mission)
    transition_mission(actor=submitting_director, mission=mission, action="submit")
    with pytest.raises(PermissionDenied):
        transition_mission(actor=submitting_director, mission=mission, action="approve")


def test_reject_requires_reason(mission_with_requirement):
    mission = mission_with_requirement
    transition_mission(actor=mission.created_by, mission=mission, action="submit")
    with pytest.raises(ApplicationError, match="reason"):
        transition_mission(actor=director_for(mission), mission=mission, action="reject")


def test_reject_then_revise_reopens_draft(mission_with_requirement):
    mission = mission_with_requirement
    transition_mission(actor=mission.created_by, mission=mission, action="submit")
    mission = transition_mission(actor=director_for(mission), mission=mission, action="reject",
                                 reason="Not enough detail")
    assert mission.status == MissionStatus.REJECTED
    mission = transition_mission(actor=mission.created_by, mission=mission, action="revise")
    assert mission.status == MissionStatus.DRAFT


def test_lead_cannot_progress_others_mission(mission_with_requirement):
    mission = mission_with_requirement
    other_lead = UserFactory(role=Role.MISSION_LEAD, tenant=mission.tenant)
    with pytest.raises(PermissionDenied):
        transition_mission(actor=other_lead, mission=mission, action="submit")


def test_crew_cannot_transition(mission_with_requirement):
    mission = mission_with_requirement
    crew = UserFactory(role=Role.CREW_MEMBER, tenant=mission.tenant)
    with pytest.raises(PermissionDenied):
        transition_mission(actor=crew, mission=mission, action="submit")


def test_activate_needs_start_date_reached(mission_with_requirement):
    mission = mission_with_requirement  # factory default: starts 10 days in the future
    transition_mission(actor=mission.created_by, mission=mission, action="submit")
    mission = transition_mission(actor=director_for(mission), mission=mission, action="approve")
    with pytest.raises(ApplicationError, match="start date"):
        transition_mission(actor=mission.created_by, mission=mission, action="activate")


def test_invalid_state_transition(mission_with_requirement):
    mission = mission_with_requirement
    with pytest.raises(ApplicationError, match="Cannot approve"):
        transition_mission(actor=director_for(mission), mission=mission, action="approve")


def test_cancel_from_terminal_forbidden(mission_with_requirement):
    mission = mission_with_requirement
    mission = transition_mission(actor=mission.created_by, mission=mission, action="cancel",
                                 reason="Scrapped")
    assert mission.status == MissionStatus.CANCELLED
    with pytest.raises(ApplicationError):
        transition_mission(actor=mission.created_by, mission=mission, action="cancel", reason="Again")
```

`backend/tests/missions/test_mission_services.py`:

```python
import pytest

from mission_control.common.exceptions import ApplicationError
from mission_control.missions.factories import MissionFactory
from mission_control.missions.models import MissionRequirement, MissionStatus
from mission_control.missions.services.missions import mission_requirements_set, mission_update
from mission_control.tenants.context import set_current_tenant_id
from mission_control.users.factories import SkillFactory

pytestmark = pytest.mark.django_db


def test_requirements_set_replaces(mission=None):
    mission = MissionFactory()
    set_current_tenant_id(mission.tenant_id)
    s1, s2 = SkillFactory(tenant=mission.tenant), SkillFactory(tenant=mission.tenant)
    mission_requirements_set(actor=mission.created_by, mission=mission, items=[
        {"skill_id": s1.id, "min_proficiency": 7, "required_count": 1},
        {"skill_id": s2.id, "min_proficiency": 4, "required_count": 2},
    ])
    mission_requirements_set(actor=mission.created_by, mission=mission, items=[
        {"skill_id": s1.id, "min_proficiency": 9, "required_count": 1},
    ])
    rows = MissionRequirement.objects.filter(mission=mission)
    assert [(r.skill_id, r.min_proficiency, r.required_count) for r in rows] == [(s1.id, 9, 1)]


def test_edit_locked_outside_draft_rejected():
    mission = MissionFactory(status=MissionStatus.ACTIVE)
    set_current_tenant_id(mission.tenant_id)
    with pytest.raises(ApplicationError):
        mission_update(actor=mission.created_by, mission=mission, name="Renamed")


def test_archived_skill_rejected_in_requirements():
    mission = MissionFactory()
    set_current_tenant_id(mission.tenant_id)
    archived = SkillFactory(tenant=mission.tenant, is_archived=True)
    with pytest.raises(ApplicationError):
        mission_requirements_set(actor=mission.created_by, mission=mission, items=[
            {"skill_id": archived.id, "min_proficiency": 5, "required_count": 1},
        ])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/missions/ -v` — Expected: FAIL (services module missing).

- [ ] **Step 3: Implement `missions/services/missions.py`**

```python
import datetime as dt
from dataclasses import dataclass

from django.db import transaction
from rest_framework.exceptions import PermissionDenied

from mission_control.common.exceptions import ApplicationError
from mission_control.missions.models import Mission, MissionRequirement, MissionStatus, MissionTransition
from mission_control.tenants.context import require_current_tenant_id
from mission_control.users.models import Skill
from mission_control.users.permissions import Permission, ensure_permission
from mission_control.users.roles import Role

S = MissionStatus


@dataclass(frozen=True)
class Transition:
    from_statuses: frozenset
    to_status: str
    permission: Permission
    requires_reason: bool = False


TRANSITIONS: dict[str, Transition] = {
    "submit": Transition(frozenset({S.DRAFT}), S.PENDING_APPROVAL, Permission.MISSION_PROGRESS),
    "approve": Transition(frozenset({S.PENDING_APPROVAL}), S.APPROVED, Permission.MISSION_REVIEW),
    "reject": Transition(frozenset({S.PENDING_APPROVAL}), S.REJECTED, Permission.MISSION_REVIEW, True),
    "revise": Transition(frozenset({S.REJECTED}), S.DRAFT, Permission.MISSION_PROGRESS),
    "activate": Transition(frozenset({S.APPROVED}), S.ACTIVE, Permission.MISSION_PROGRESS),
    "complete": Transition(frozenset({S.ACTIVE}), S.COMPLETED, Permission.MISSION_PROGRESS),
    "cancel": Transition(
        frozenset({S.DRAFT, S.PENDING_APPROVAL, S.APPROVED, S.REJECTED, S.ACTIVE}),
        S.CANCELLED, Permission.MISSION_PROGRESS, True,
    ),
}


def _ensure_owns_or_director(actor, mission):
    if actor.role != Role.DIRECTOR and mission.created_by_id != actor.id:
        raise PermissionDenied("You can only manage missions you created.")


def _submitter_id(mission) -> int | None:
    latest = (mission.transitions.filter(to_status=S.PENDING_APPROVAL)
              .order_by("-created_at").first())
    return latest.actor_id if latest else None


def _validate_staffing_for_approval(mission):
    """Stage 4 wires the real staffing validation here (coverage, crew bounds, hard conflicts)."""
    return None


def _run_guards(action, actor, mission):
    if action == "submit" and not mission.requirements.exists():
        raise ApplicationError("Add at least one skill requirement before submitting.")
    if action in ("approve", "reject") and actor.id in {mission.created_by_id, _submitter_id(mission)}:
        raise PermissionDenied("You cannot review your own mission.")
    if action == "approve":
        _validate_staffing_for_approval(mission)
    if action == "activate":
        if mission.start_date > dt.date.today():
            raise ApplicationError("Mission cannot activate before its start date.")
        _validate_staffing_for_approval(mission)
    if action == "complete" and mission.end_date > dt.date.today():
        raise ApplicationError("Mission cannot complete before its end date.")


@transaction.atomic
def transition_mission(*, actor, mission: Mission, action: str, reason: str | None = None) -> Mission:
    if action not in TRANSITIONS:
        raise ApplicationError(f"Unknown action '{action}'.")
    spec = TRANSITIONS[action]
    ensure_permission(actor, spec.permission)
    mission = Mission.objects.select_for_update().get(id=mission.id)
    if spec.permission == Permission.MISSION_PROGRESS:
        _ensure_owns_or_director(actor, mission)
    if mission.status not in spec.from_statuses:
        raise ApplicationError(f"Cannot {action} a mission in state '{mission.status}'.")
    if spec.requires_reason and not (reason and reason.strip()):
        raise ApplicationError(f"A reason is required to {action}.")
    _run_guards(action, actor, mission)
    from_status = mission.status
    mission.status = spec.to_status
    mission.save(update_fields=["status", "updated_at"])
    MissionTransition.objects.create(
        mission=mission, from_status=from_status, to_status=spec.to_status,
        actor=actor, reason=reason or "",
    )
    return mission
```

Plus `mission_create`, `mission_update`, `mission_requirements_set` (same file):

```python
def mission_create(*, actor, name, description, start_date, end_date, min_crew, max_crew) -> Mission:
    mission = Mission(name=name, description=description, start_date=start_date, end_date=end_date,
                      min_crew=min_crew, max_crew=max_crew, created_by=actor)
    mission.full_clean(exclude=["tenant"])
    mission.save()
    return mission


EDITABLE_STATUSES = frozenset({S.DRAFT, S.REJECTED})


def mission_update(*, actor, mission: Mission, **fields) -> Mission:
    _ensure_owns_or_director(actor, mission)
    if mission.status not in EDITABLE_STATUSES:
        raise ApplicationError("Mission can only be edited in draft or rejected state.")
    for attr in ("name", "description", "start_date", "end_date", "min_crew", "max_crew"):
        if attr in fields:
            setattr(mission, attr, fields[attr])
    mission.full_clean(exclude=["tenant"])
    mission.save()
    return mission


@transaction.atomic
def mission_requirements_set(*, actor, mission: Mission, items: list[dict]) -> None:
    _ensure_owns_or_director(actor, mission)
    if mission.status not in EDITABLE_STATUSES:
        raise ApplicationError("Requirements can only be edited in draft or rejected state.")
    pairs = [(i["skill_id"], i["min_proficiency"]) for i in items]
    if len(pairs) != len(set(pairs)):
        raise ApplicationError("Duplicate skill/proficiency requirement rows.")
    skill_ids = {i["skill_id"] for i in items}
    valid = set(Skill.objects.filter(id__in=skill_ids, is_archived=False).values_list("id", flat=True))
    if skill_ids - valid:
        raise ApplicationError("Unknown or archived skills.", extra={"skill_ids": sorted(skill_ids - valid)})
    mission.requirements.all().delete()
    MissionRequirement.objects_unscoped.bulk_create([
        MissionRequirement(tenant_id=require_current_tenant_id(), mission=mission,
                           skill_id=i["skill_id"], min_proficiency=i["min_proficiency"],
                           required_count=i["required_count"])
        for i in items
    ])
```

`missions/selectors/missions.py`:

```python
from django.shortcuts import get_object_or_404

from mission_control.missions.models import Mission


def mission_list(*, status: str | None = None, search: str | None = None):
    qs = Mission.objects.select_related("created_by").order_by("-created_at")
    if status:
        qs = qs.filter(status=status)
    if search:
        qs = qs.filter(name__icontains=search)
    return qs


def mission_get(mission_id: int) -> Mission:
    qs = Mission.objects.select_related("created_by").prefetch_related(
        "requirements__skill", "transitions__actor"
    )
    return get_object_or_404(qs, id=mission_id)
```

- [ ] **Step 4: Run tests to verify they pass, commit**

Run: `uv run pytest tests/missions/ -v` — Expected: PASS.

```bash
git add -A && git commit -m "feat: mission FSM service with per-transition permissions and guards"
```

---

### Task 3.3: Mission APIs

**Files:**
- Create: `backend/mission_control/missions/apis/{__init__.py,missions.py}`, `backend/tests/missions/test_mission_apis.py`
- Modify: `backend/mission_control/missions/urls.py`

**Interfaces:**
- Produces:
  - `GET /api/v1/missions/` (perm `mission.view`; query `status`, `search`) — paginated `{id, name, status, start_date, end_date, min_crew, max_crew, created_by: {id, name}}`
  - `POST /api/v1/missions/` (perm `mission.create`) — input `{name, description?, start_date, end_date, min_crew, max_crew}` → 201 detail
  - `GET /api/v1/missions/<id>/` (perm `mission.view`) — detail = list shape + `description` + `requirements: [{id, skill_id, skill_name, min_proficiency, required_count}]` + `history: [{from_status, to_status, actor_name, reason, created_at}]`
  - `PATCH /api/v1/missions/<id>/` (perm `mission.edit`) — partial mission fields
  - `PUT /api/v1/missions/<id>/requirements/` (perm `mission.edit`) — `{items: [{skill_id, min_proficiency, required_count}]}` → detail
  - `POST /api/v1/missions/<id>/transitions/` — `{action, reason?}`; **no static perm** (the FSM table owns it) → detail
- Consumes: everything from Task 3.2

- [ ] **Step 1: Write the failing tests**

`backend/tests/missions/test_mission_apis.py`:

```python
import pytest

from mission_control.missions.factories import MissionFactory, MissionRequirementFactory
from mission_control.users.factories import UserFactory
from mission_control.users.roles import Role

pytestmark = pytest.mark.django_db


def test_lead_creates_mission(auth_client_for):
    lead = UserFactory(role=Role.MISSION_LEAD)
    resp = auth_client_for(lead).post("/api/v1/missions/", {
        "name": "Ganymede Survey", "start_date": "2026-09-01", "end_date": "2026-09-14",
        "min_crew": 2, "max_crew": 4,
    })
    assert resp.status_code == 201
    assert resp.data["status"] == "draft"


def test_crew_cannot_list_missions(auth_client_for):
    crew = UserFactory(role=Role.CREW_MEMBER)
    assert auth_client_for(crew).get("/api/v1/missions/").status_code == 403


def test_status_filter(auth_client_for):
    lead = UserFactory(role=Role.MISSION_LEAD)
    MissionFactory(tenant=lead.tenant, created_by=lead, status="active", name="Live one")
    MissionFactory(tenant=lead.tenant, created_by=lead, name="Draft one")
    resp = auth_client_for(lead).get("/api/v1/missions/?status=active")
    assert [m["name"] for m in resp.data["results"]] == ["Live one"]


def test_cross_tenant_mission_404(auth_client_for):
    lead = UserFactory(role=Role.MISSION_LEAD)
    other = MissionFactory()  # other tenant
    assert auth_client_for(lead).get(f"/api/v1/missions/{other.id}/").status_code == 404


def test_full_lifecycle_via_api(auth_client_for):
    lead = UserFactory(role=Role.MISSION_LEAD)
    director = UserFactory(role=Role.DIRECTOR, tenant=lead.tenant)
    mission = MissionFactory(tenant=lead.tenant, created_by=lead)
    MissionRequirementFactory(mission=mission)
    lead_client, director_client = auth_client_for(lead), auth_client_for(director)

    url = f"/api/v1/missions/{mission.id}/transitions/"
    assert lead_client.post(url, {"action": "submit"}).status_code == 200
    resp = director_client.post(url, {"action": "reject", "reason": "Dates clash with resupply"})
    assert resp.status_code == 200 and resp.data["status"] == "rejected"
    assert lead_client.post(url, {"action": "revise"}).status_code == 200
    resp = lead_client.get(f"/api/v1/missions/{mission.id}/")
    assert [h["to_status"] for h in resp.data["history"]] == ["draft", "rejected", "pending_approval"]


def test_requirements_put(auth_client_for):
    from mission_control.users.factories import SkillFactory
    lead = UserFactory(role=Role.MISSION_LEAD)
    mission = MissionFactory(tenant=lead.tenant, created_by=lead)
    skill = SkillFactory(tenant=lead.tenant)
    resp = auth_client_for(lead).put(f"/api/v1/missions/{mission.id}/requirements/", {
        "items": [{"skill_id": skill.id, "min_proficiency": 6, "required_count": 2}],
    }, format="json")
    assert resp.status_code == 200
    assert resp.data["requirements"][0]["min_proficiency"] == 6
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/missions/test_mission_apis.py -v` — Expected: FAIL.

- [ ] **Step 3: Implement `missions/apis/missions.py`**

Follow the Stage 2 API idiom exactly. Serializers (inline classes on the APIViews):

```python
class MissionListItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    status = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    min_crew = serializers.IntegerField()
    max_crew = serializers.IntegerField()
    created_by = serializers.SerializerMethodField()

    def get_created_by(self, m):
        return {"id": m.created_by_id, "name": m.created_by.name}


class MissionDetailSerializer(MissionListItemSerializer):
    description = serializers.CharField()
    requirements = serializers.SerializerMethodField()
    history = serializers.SerializerMethodField()

    def get_requirements(self, m):
        return [{"id": r.id, "skill_id": r.skill_id, "skill_name": r.skill.name,
                 "min_proficiency": r.min_proficiency, "required_count": r.required_count}
                for r in m.requirements.all()]

    def get_history(self, m):
        return [{"from_status": t.from_status, "to_status": t.to_status,
                 "actor_name": t.actor.name, "reason": t.reason, "created_at": t.created_at}
                for t in m.transitions.all()]
```

Views: `MissionListCreateApi` (get: `mission.view` + `mission_list(status=..., search=...)`; post: `mission.create` + input serializer `{name, description(default "")​, start_date, end_date, min_crew(min_value=1), max_crew(min_value=1)}` → `mission_create` → 201 `MissionDetailSerializer` via `mission_get`), `MissionDetailApi` (get / patch), `MissionRequirementsApi` (put: items child serializer `{skill_id, min_proficiency(1..10), required_count(min_value=1)}` → `mission_requirements_set` → fresh `mission_get`), `MissionTransitionApi` (post: `{action: CharField, reason: CharField(required=False, allow_blank=True)}` → `transition_mission(actor=request.user, mission=selectors.mission_get(id), action=..., reason=...)` → fresh detail). After PATCH/PUT/transition always re-serialize via `mission_get(mission_id)` so requirements/history are prefetched.

`missions/urls.py`:

```python
from django.urls import path

from mission_control.missions.apis.missions import (
    MissionDetailApi, MissionListCreateApi, MissionRequirementsApi, MissionTransitionApi,
)

urlpatterns = [
    path("missions/", MissionListCreateApi.as_view()),
    path("missions/<int:mission_id>/", MissionDetailApi.as_view()),
    path("missions/<int:mission_id>/requirements/", MissionRequirementsApi.as_view()),
    path("missions/<int:mission_id>/transitions/", MissionTransitionApi.as_view()),
]
```

- [ ] **Step 4: Run tests to verify they pass, commit**

Run: `uv run pytest tests/ -v` — Expected: PASS.

```bash
git add -A && git commit -m "feat: mission CRUD, requirements, and transition APIs"
```

---

### Task 3.4: Frontend — missions list + create

**Files:**
- Create: `frontend/src/features/missions/api/missions.ts`, `frontend/src/features/missions/components/{missions-page.tsx,mission-create-dialog.tsx,mission-status-badge.tsx}`, `frontend/src/features/missions/missions.test.tsx`
- Modify: `frontend/src/app/router.tsx`, `frontend/src/testing/mocks.ts`

**Interfaces:**
- Produces:
  - `features/missions/api/missions.ts`:
    - `MISSION_STATUSES = ["draft","pending_approval","approved","active","completed","rejected","cancelled"] as const`; `MissionStatusSchema = z.enum(MISSION_STATUSES)`
    - `MissionSchema` (list shape per Task 3.3), `MissionDetailSchema` (+`description`, `requirements`, `history`)
    - `useMissions(status?: string)` (key `["missions", {status}]`), `useMission(id)` (key `["missions", id]`), `useCreateMission()`, `useUpdateMission(id)`, `useSetRequirements(id)`, `useTransitionMission(id)` — mutations invalidate `["missions"]`
  - `mission-status-badge.tsx`: `<MissionStatusBadge status/>` — colored shadcn `Badge` (draft=secondary, pending_approval=amber, approved=blue, active=green, completed=default, rejected/cancelled=destructive/muted)
  - `/missions`: status filter `Tabs` (All + each status), table rows (name → link `/missions/:id`, status badge, dates, crew range, lead name), "New mission" `Button` → `mission-create-dialog` (name, description, start/end date inputs, min/max crew) — dialog per the "big create" pattern
- Consumes: `PaginatedSchema` from `features/skills/api/skills.ts`

- [ ] **Step 1: Write the failing test**

`frontend/src/features/missions/missions.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { RouterProvider } from "react-router-dom";
import { AppProvider } from "@/app/provider";
import { createRouter } from "@/app/router";

describe("missions list", () => {
  it("lists missions and opens the create dialog", async () => {
    render(<AppProvider><RouterProvider router={createRouter(["/missions"])} /></AppProvider>);
    expect(await screen.findByText("Ganymede Survey")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /new mission/i }));
    expect(await screen.findByLabelText(/name/i)).toBeInTheDocument();
  });
});
```

Add to `mocks.ts` a `missionFixture` (draft, id 10, name "Ganymede Survey", requirements + empty history) and handlers for `GET /api/v1/missions/` (paginated) and `GET /api/v1/missions/10/`.

Run: `npm test -- --run` — Expected: FAIL.

- [ ] **Step 2: Implement** per Interfaces. Replace the `/missions` placeholder route with `<RequirePermission permission="mission.view"><MissionsPage /></RequirePermission>`.

- [ ] **Step 3: Verify green, commit**

```bash
npm test -- --run && npm run build
git add -A && git commit -m "feat: missions list with status tabs and create dialog"
```

---

### Task 3.5: Frontend — mission detail

**Files:**
- Create: `frontend/src/features/missions/components/{mission-detail-page.tsx,requirements-editor.tsx,transition-buttons.tsx,mission-history.tsx}`, `frontend/src/features/missions/mission-detail.test.tsx`
- Modify: `frontend/src/app/router.tsx` (add `/missions/:missionId`)

**Interfaces:**
- Produces:
  - `/missions/:missionId` — header: name, `MissionStatusBadge`, dates, crew range, lead; description below; sections: Requirements, Staffing (placeholder `<section>` replaced in Stage 4), History
  - `transition-buttons.tsx`: available actions computed from `status` + `user` — draft→Submit (`mission.progress`), pending_approval→Approve/Reject (`mission.review`, hidden when `user.id === mission.created_by.id`), rejected→Revise, approved→Activate, active→Complete, plus Cancel on any non-terminal (`mission.progress`). Reject/Cancel open a small `Dialog` requiring a reason. Errors → `toast.error(envelope.message)`.
  - `requirements-editor.tsx`: read-only rows (skill name, "≥ N", "× count") when status ∉ {draft, rejected}; otherwise editable rows (skill `Select` from non-archived `useSkills()`, min proficiency `Select` 1–10, count `Input`), add/remove row, Save → `useSetRequirements`
  - `mission-history.tsx`: reverse-chronological list — "`actor_name` moved `from_status` → `to_status`", reason in muted text, timestamp
- Consumes: Task 3.4 api hooks; `useUser`, `hasPermission`

- [ ] **Step 1: Write the failing test**

`frontend/src/features/missions/mission-detail.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { RouterProvider } from "react-router-dom";
import { AppProvider } from "@/app/provider";
import { createRouter } from "@/app/router";
import { missionFixture, server } from "@/testing/mocks";

describe("mission detail", () => {
  it("submits a draft mission", async () => {
    let posted: unknown = null;
    server.use(http.post("/api/v1/missions/10/transitions/", async ({ request }) => {
      posted = await request.json();
      return HttpResponse.json({ ...missionFixture, status: "pending_approval", history: [] });
    }));
    render(<AppProvider><RouterProvider router={createRouter(["/missions/10"])} /></AppProvider>);
    await userEvent.click(await screen.findByRole("button", { name: /submit/i }));
    expect(posted).toEqual({ action: "submit" });
  });

  it("reject requires a reason via dialog", async () => {
    server.use(http.get("/api/v1/missions/10/", () =>
      HttpResponse.json({ ...missionFixture, status: "pending_approval", created_by: { id: 99, name: "Other" } })));
    render(<AppProvider><RouterProvider router={createRouter(["/missions/10"])} /></AppProvider>);
    // default mock user is a lead without mission.review — no approve/reject rendered
    expect(await screen.findByRole("heading", { name: missionFixture.name })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /approve/i })).not.toBeInTheDocument();
  });
});
```

Run: `npm test -- --run` — Expected: FAIL.

- [ ] **Step 2: Implement** the four components per Interfaces; wire route.

- [ ] **Step 3: Verify green + manual smoke, commit**

Manual: seed a draft mission via UI as lead → submit → log in as director → reject with reason → revise as lead → history shows all steps.

```bash
npm test -- --run && npm run build
git add -A && git commit -m "feat: mission detail with requirements editor, transitions, history"
```

---

**Stage 3 exit criteria:** suites green · full lifecycle draft→submit→reject→revise→submit→approve driveable from the UI by lead+director · requirements editable only in draft/rejected · history timeline accurate · cross-tenant access 404s proven.
