# Stage 4: Assignments & Availability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Global constraints in `00-overview.md` apply to every task.

**Goal:** Assignment lifecycle (propose → accept/decline, remove), the single availability/coverage source (`selectors/staffing.py`), staffing APIs, the approve/activate staffing guard, staffing panel UI, and the crew my-assignments flow.

**Architecture:** Availability has exactly one implementation, consumed by staffing API, matcher (Stage 5), and FSM guards. Approvals serialize on the crew members' `User` rows (`select_for_update`) so two missions can't both claim the same person.

**Tech Stack:** See `00-overview.md`.

---

### Task 4.1: Assignment model

**Files:**
- Create: migrations `missions/0003_assignment.py` (generated) + `missions/0004_assignment_composite_fks.py`, `backend/tests/missions/test_assignment_model.py`
- Modify: `backend/mission_control/missions/models.py`, `backend/mission_control/missions/factories.py`

**Interfaces:**
- Produces:
  - `missions.models.AssignmentStatus` (TextChoices): `PROPOSED="proposed"`, `ACCEPTED="accepted"`, `DECLINED="declined"`, `REMOVED="removed"`; `LIVE_ASSIGNMENT_STATUSES = frozenset({PROPOSED, ACCEPTED})`
  - `missions.models.Assignment(TenantModel)`: `mission` FK (CASCADE, related_name `assignments`), `user` FK (CASCADE, related_name `assignments`), `status` (default PROPOSED), `decline_reason` (blank), `created_by` FK (PROTECT, `+`), `responded_at` (nullable DateTime). **Partial unique**: `UniqueConstraint(fields=["mission","user"], condition=Q(status__in=["proposed","accepted"]), name="assignment_live_uniq")`
  - Composite FKs (0004): `(tenant_id, mission_id) → missions_mission(tenant_id, id)`, `(tenant_id, user_id) → users_user(tenant_id, id)`
  - `missions.factories.AssignmentFactory` (mission SubFactory; user = crew member of same tenant; `created_by` = mission.created_by; tenant from mission)

- [ ] **Step 1: Write the failing tests**

`backend/tests/missions/test_assignment_model.py`:

```python
import pytest
from django.db import IntegrityError

from mission_control.missions.factories import AssignmentFactory
from mission_control.missions.models import AssignmentStatus

pytestmark = pytest.mark.django_db


def test_second_live_assignment_for_same_pair_blocked():
    a = AssignmentFactory(status=AssignmentStatus.ACCEPTED)
    with pytest.raises(IntegrityError):
        AssignmentFactory(mission=a.mission, user=a.user, status=AssignmentStatus.PROPOSED)


def test_reproposing_after_decline_is_allowed():
    a = AssignmentFactory(status=AssignmentStatus.DECLINED)
    again = AssignmentFactory(mission=a.mission, user=a.user)  # proposed
    assert again.pk != a.pk
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/missions/test_assignment_model.py -v` — Expected: FAIL.

- [ ] **Step 3: Implement** — append to `missions/models.py`:

```python
class AssignmentStatus(models.TextChoices):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    REMOVED = "removed"


LIVE_ASSIGNMENT_STATUSES = frozenset({AssignmentStatus.PROPOSED, AssignmentStatus.ACCEPTED})


class Assignment(TenantModel):
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name="assignments")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="assignments")
    status = models.CharField(max_length=16, choices=AssignmentStatus.choices,
                              default=AssignmentStatus.PROPOSED)
    decline_reason = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="+")
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["mission", "user"],
                condition=Q(status__in=["proposed", "accepted"]),
                name="assignment_live_uniq",
            ),
        ]
```

Factory:

```python
class AssignmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Assignment

    mission = factory.SubFactory(MissionFactory)
    tenant = factory.SelfAttribute("mission.tenant")
    user = factory.SubFactory(UserFactory, role=Role.CREW_MEMBER,
                              tenant=factory.SelfAttribute("..mission.tenant"))
    created_by = factory.SelfAttribute("mission.created_by")
```

Generate 0003, hand-write 0004 (RunSQL pattern from Stage 2 Task 2.1).

- [ ] **Step 4: Run tests, commit**

```bash
uv run pytest tests/ -v
git add -A && git commit -m "feat: Assignment model with live partial-unique and composite FKs"
```

---

### Task 4.2: Staffing selectors — availability + coverage

**Files:**
- Create: `backend/mission_control/missions/selectors/staffing.py`, `backend/tests/missions/test_staffing.py`

**Interfaces:**
- Produces (`missions.selectors.staffing`):
  - `HARD_BLOCK_MISSION_STATUSES = frozenset({MissionStatus.APPROVED, MissionStatus.ACTIVE})`
  - `hard_blocked_user_ids(*, start_date, end_date, exclude_mission_id=None) -> set[int]` — users with an *accepted* assignment on an *approved/active* mission overlapping the range
  - `soft_conflicts_for_users(*, user_ids, start_date, end_date, exclude_mission_id) -> dict[int, list[dict]]` — per user: live assignments on other missions overlapping the range that are **not** hard blocks; entries `{"mission_id", "mission_name", "mission_status", "assignment_status"}`
  - `mission_coverage(mission) -> CoverageReport` — dataclasses:
    - `RequirementCoverage(requirement_id, skill_id, skill_name, min_proficiency, required_count, filled_count, filled_by: list[dict])` (`filled_by` entries `{"user_id", "name", "proficiency"}`)
    - `CoverageReport(requirements: list[RequirementCoverage], accepted_count: int, fully_covered: bool)`
    - Semantics per spec §9: per skill, requirement rows sorted by `min_proficiency` desc, qualified accepted crew sorted by proficiency desc, greedy assignment; one member fills ≤1 seat per skill but may fill seats across different skills
  - `staffing_validation_errors(mission) -> list[str]` — human-readable errors: uncovered requirements ("Requirement Piloting ≥7 needs 2, has 1"), accepted count outside `[min_crew, max_crew]`, accepted members hard-blocked elsewhere ("Ada Lovelace is committed to 'Ganymede Survey'")
- Consumes: `Assignment`, `CrewSkill`, `LIVE_ASSIGNMENT_STATUSES`

- [ ] **Step 1: Write the failing tests**

`backend/tests/missions/test_staffing.py`:

```python
import datetime as dt

import pytest

from mission_control.missions.factories import (
    AssignmentFactory, MissionFactory, MissionRequirementFactory,
)
from mission_control.missions.models import AssignmentStatus, MissionStatus
from mission_control.missions.selectors.staffing import (
    hard_blocked_user_ids, mission_coverage, soft_conflicts_for_users, staffing_validation_errors,
)
from mission_control.tenants.context import set_current_tenant_id
from mission_control.users.factories import CrewSkillFactory, SkillFactory, UserFactory
from mission_control.users.roles import Role

pytestmark = pytest.mark.django_db

D = dt.date


@pytest.fixture
def tenant_ctx():
    mission = MissionFactory(start_date=D(2026, 9, 1), end_date=D(2026, 9, 10))
    set_current_tenant_id(mission.tenant_id)
    return mission


def crew_with(mission, skill, proficiency, name="Crew"):
    user = UserFactory(role=Role.CREW_MEMBER, tenant=mission.tenant, name=name)
    CrewSkillFactory(user=user, skill=skill, proficiency=proficiency)
    return user


def test_hard_block_only_from_accepted_on_approved_or_active(tenant_ctx):
    mission = tenant_ctx
    blocker = MissionFactory(tenant=mission.tenant, status=MissionStatus.APPROVED,
                             start_date=D(2026, 9, 5), end_date=D(2026, 9, 15))
    soft_m = MissionFactory(tenant=mission.tenant, status=MissionStatus.PENDING_APPROVAL,
                            start_date=D(2026, 9, 5), end_date=D(2026, 9, 15))
    hard_user = AssignmentFactory(mission=blocker, status=AssignmentStatus.ACCEPTED).user
    proposed_user = AssignmentFactory(mission=blocker, status=AssignmentStatus.PROPOSED).user
    soft_user = AssignmentFactory(mission=soft_m, status=AssignmentStatus.ACCEPTED).user

    blocked = hard_blocked_user_ids(start_date=mission.start_date, end_date=mission.end_date)
    assert hard_user.id in blocked
    assert proposed_user.id not in blocked and soft_user.id not in blocked


def test_no_block_when_dates_do_not_overlap(tenant_ctx):
    mission = tenant_ctx
    blocker = MissionFactory(tenant=mission.tenant, status=MissionStatus.ACTIVE,
                             start_date=D(2026, 9, 11), end_date=D(2026, 9, 20))
    user = AssignmentFactory(mission=blocker, status=AssignmentStatus.ACCEPTED).user
    assert user.id not in hard_blocked_user_ids(start_date=mission.start_date, end_date=mission.end_date)


def test_soft_conflicts_reported(tenant_ctx):
    mission = tenant_ctx
    other = MissionFactory(tenant=mission.tenant, status=MissionStatus.DRAFT,
                           start_date=D(2026, 9, 5), end_date=D(2026, 9, 15), name="Draft Op")
    a = AssignmentFactory(mission=other, status=AssignmentStatus.ACCEPTED)
    conflicts = soft_conflicts_for_users(
        user_ids=[a.user_id], start_date=mission.start_date,
        end_date=mission.end_date, exclude_mission_id=mission.id,
    )
    assert conflicts[a.user_id][0]["mission_name"] == "Draft Op"


def test_coverage_multi_row_same_skill(tenant_ctx):
    mission = tenant_ctx
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=9, required_count=1)
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5, required_count=2)
    for prof in (9, 6, 5):
        user = crew_with(mission, piloting, prof)
        AssignmentFactory(mission=mission, user=user, status=AssignmentStatus.ACCEPTED)
    report = mission_coverage(mission)
    assert report.fully_covered
    seat9 = next(r for r in report.requirements if r.min_proficiency == 9)
    assert [f["proficiency"] for f in seat9.filled_by] == [9]


def test_generalist_covers_two_skills_but_one_seat_per_skill(tenant_ctx):
    mission = tenant_ctx
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    nav = SkillFactory(tenant=mission.tenant, name="Navigation")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5, required_count=1)
    MissionRequirementFactory(mission=mission, skill=nav, min_proficiency=5, required_count=1)
    generalist = crew_with(mission, piloting, 8)
    CrewSkillFactory(user=generalist, skill=nav, proficiency=7)
    AssignmentFactory(mission=mission, user=generalist, status=AssignmentStatus.ACCEPTED)
    report = mission_coverage(mission)
    assert report.fully_covered  # one person, two different-skill seats


def test_proposed_assignments_do_not_count(tenant_ctx):
    mission = tenant_ctx
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=5, required_count=1)
    user = crew_with(mission, piloting, 8)
    AssignmentFactory(mission=mission, user=user, status=AssignmentStatus.PROPOSED)
    report = mission_coverage(mission)
    assert not report.fully_covered


def test_validation_errors_list_problems(tenant_ctx):
    mission = tenant_ctx  # min_crew=1, no requirements covered yet
    piloting = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=piloting, min_proficiency=7, required_count=2)
    errors = staffing_validation_errors(mission)
    assert any("Piloting" in e for e in errors)
    assert any("min_crew" in e or "at least" in e for e in errors)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/missions/test_staffing.py -v` — Expected: FAIL.

- [ ] **Step 3: Implement `missions/selectors/staffing.py`**

```python
import datetime as dt
from collections import defaultdict
from dataclasses import dataclass, field

from mission_control.missions.models import (
    Assignment, AssignmentStatus, LIVE_ASSIGNMENT_STATUSES, Mission, MissionStatus,
)
from mission_control.users.models import CrewSkill

HARD_BLOCK_MISSION_STATUSES = frozenset({MissionStatus.APPROVED, MissionStatus.ACTIVE})


def _overlapping(qs, start_date, end_date):
    return qs.filter(mission__start_date__lte=end_date, mission__end_date__gte=start_date)


def hard_blocked_user_ids(*, start_date, end_date, exclude_mission_id=None) -> set[int]:
    qs = Assignment.objects.filter(
        status=AssignmentStatus.ACCEPTED,
        mission__status__in=HARD_BLOCK_MISSION_STATUSES,
    )
    if exclude_mission_id:
        qs = qs.exclude(mission_id=exclude_mission_id)
    return set(_overlapping(qs, start_date, end_date).values_list("user_id", flat=True))


def soft_conflicts_for_users(*, user_ids, start_date, end_date, exclude_mission_id) -> dict[int, list[dict]]:
    qs = (
        Assignment.objects.filter(user_id__in=user_ids, status__in=LIVE_ASSIGNMENT_STATUSES)
        .exclude(mission_id=exclude_mission_id)
        .exclude(status=AssignmentStatus.ACCEPTED, mission__status__in=HARD_BLOCK_MISSION_STATUSES)
        .exclude(mission__status__in=[MissionStatus.COMPLETED, MissionStatus.CANCELLED])
        .select_related("mission")
    )
    result: dict[int, list[dict]] = defaultdict(list)
    for a in _overlapping(qs, start_date, end_date):
        result[a.user_id].append({
            "mission_id": a.mission_id, "mission_name": a.mission.name,
            "mission_status": a.mission.status, "assignment_status": a.status,
        })
    return dict(result)


@dataclass
class RequirementCoverage:
    requirement_id: int
    skill_id: int
    skill_name: str
    min_proficiency: int
    required_count: int
    filled_count: int = 0
    filled_by: list = field(default_factory=list)


@dataclass
class CoverageReport:
    requirements: list
    accepted_count: int
    fully_covered: bool


def mission_coverage(mission: Mission) -> CoverageReport:
    accepted = list(
        Assignment.objects.filter(mission=mission, status=AssignmentStatus.ACCEPTED)
        .select_related("user")
    )
    accepted_users = {a.user_id: a.user for a in accepted}
    prof_by_user_skill = {
        (cs.user_id, cs.skill_id): cs.proficiency
        for cs in CrewSkill.objects.filter(user_id__in=accepted_users)
    }
    coverages = [
        RequirementCoverage(r.id, r.skill_id, r.skill.name, r.min_proficiency, r.required_count)
        for r in mission.requirements.select_related("skill").all()
    ]
    by_skill: dict[int, list[RequirementCoverage]] = defaultdict(list)
    for cov in coverages:
        by_skill[cov.skill_id].append(cov)

    for skill_id, rows in by_skill.items():
        rows.sort(key=lambda c: -c.min_proficiency)
        qualified = sorted(
            ((prof_by_user_skill.get((uid, skill_id), 0), uid) for uid in accepted_users),
            reverse=True,
        )
        available = [(prof, uid) for prof, uid in qualified if prof > 0]
        for cov in rows:  # most demanding first; hand the highest remaining member to each seat
            while cov.filled_count < cov.required_count and available:
                prof, uid = available[0]
                if prof < cov.min_proficiency:
                    break  # nobody left qualifies for this row (list is sorted desc)
                available.pop(0)
                cov.filled_count += 1
                cov.filled_by.append(
                    {"user_id": uid, "name": accepted_users[uid].name, "proficiency": prof}
                )

    fully = all(c.filled_count >= c.required_count for c in coverages)
    return CoverageReport(requirements=coverages, accepted_count=len(accepted), fully_covered=fully)


def staffing_validation_errors(mission: Mission) -> list[str]:
    report = mission_coverage(mission)
    errors = []
    for cov in report.requirements:
        if cov.filled_count < cov.required_count:
            errors.append(
                f"Requirement {cov.skill_name} ≥{cov.min_proficiency} needs "
                f"{cov.required_count}, has {cov.filled_count}."
            )
    if report.accepted_count < mission.min_crew:
        errors.append(
            f"Mission needs at least {mission.min_crew} accepted crew (min_crew); "
            f"has {report.accepted_count}."
        )
    if report.accepted_count > mission.max_crew:
        errors.append(f"Mission exceeds max_crew ({mission.max_crew}).")
    blocked = hard_blocked_user_ids(
        start_date=mission.start_date, end_date=mission.end_date, exclude_mission_id=mission.id
    )
    for a in Assignment.objects.filter(
        mission=mission, status=AssignmentStatus.ACCEPTED, user_id__in=blocked
    ).select_related("user"):
        conflicts = Assignment.objects.filter(
            user_id=a.user_id, status=AssignmentStatus.ACCEPTED,
            mission__status__in=HARD_BLOCK_MISSION_STATUSES,
            mission__start_date__lte=mission.end_date, mission__end_date__gte=mission.start_date,
        ).exclude(mission_id=mission.id).select_related("mission").first()
        errors.append(f"{a.user.name} is committed to '{conflicts.mission.name}'.")
    return errors
```

- [ ] **Step 4: Run tests to verify they pass, commit**

Run: `uv run pytest tests/missions/ -v` — Expected: PASS.

```bash
git add -A && git commit -m "feat: staffing selectors — availability, coverage, validation errors"
```

---

### Task 4.3: Assignment services + APIs

**Files:**
- Create: `backend/mission_control/missions/services/assignments.py`, `backend/mission_control/missions/apis/assignments.py`, `backend/tests/missions/test_assignment_apis.py`
- Modify: `backend/mission_control/missions/selectors/missions.py` (add `my_assignments`, `mission_assignments`), `backend/mission_control/missions/urls.py`

**Interfaces:**
- Produces (`missions.services.assignments`):
  - `assignments_propose(*, actor, mission, user_ids: list[int]) -> list[Assignment]` — ownership rule (lead owns / director); mission non-terminal; users must be active CREW_MEMBERs of the tenant, not already live-assigned to this mission, **not hard-blocked** for the mission range (`ApplicationError` naming them); live count + new ≤ `max_crew`
  - `assignment_remove(*, actor, assignment) -> Assignment` — ownership via `assignment.mission`; live statuses only; → REMOVED
  - `assignment_respond(*, actor, assignment, action: str, reason: str = "") -> Assignment` — `actor` must be `assignment.user` (else `PermissionDenied`); status must be PROPOSED; mission not COMPLETED/CANCELLED; `action ∈ {accept, decline}` → ACCEPTED/DECLINED, sets `responded_at=timezone.now()`, `decline_reason`
- Produces (selectors): `my_assignments(user)` (select_related mission, newest first) · `mission_assignments(mission)` (select_related user, newest first)
- Produces (APIs):
  - `GET /api/v1/missions/<id>/staffing/` (perm `mission.view`) → `{requirements: [...], accepted_count, min_crew, max_crew, fully_covered, roster: [{assignment_id, user_id, name, status, soft_conflicts: [...], hard_blocked: bool}]}` — roster = live assignments; `soft_conflicts` entries from `soft_conflicts_for_users`; `hard_blocked` from `hard_blocked_user_ids(..., exclude_mission_id=mission.id)`
  - `POST /api/v1/missions/<id>/assignments/` (perm `assignment.manage`) `{user_ids: [int]}` → 201, staffing payload
  - `POST /api/v1/assignments/<id>/remove/` (perm `assignment.manage`) → staffing payload
  - `GET /api/v1/me/assignments/` (perm `assignment.respond`) → `{results: [{id, status, decline_reason, responded_at, mission: {id, name, status, start_date, end_date, description}}]}` (unpaginated list is fine at crew scale)
  - `POST /api/v1/assignments/<id>/respond/` (perm `assignment.respond`) `{action, reason?}` → the updated row (my-assignments shape)

- [ ] **Step 1: Write the failing tests**

`backend/tests/missions/test_assignment_apis.py`:

```python
import datetime as dt

import pytest

from mission_control.missions.factories import AssignmentFactory, MissionFactory
from mission_control.missions.models import Assignment, AssignmentStatus, MissionStatus
from mission_control.users.factories import UserFactory
from mission_control.users.roles import Role

pytestmark = pytest.mark.django_db
D = dt.date


def make_lead_mission():
    lead = UserFactory(role=Role.MISSION_LEAD)
    mission = MissionFactory(tenant=lead.tenant, created_by=lead,
                             start_date=D(2026, 9, 1), end_date=D(2026, 9, 10))
    return lead, mission


def test_bulk_propose(auth_client_for):
    lead, mission = make_lead_mission()
    crew = [UserFactory(role=Role.CREW_MEMBER, tenant=lead.tenant) for _ in range(2)]
    resp = auth_client_for(lead).post(f"/api/v1/missions/{mission.id}/assignments/",
                                      {"user_ids": [c.id for c in crew]}, format="json")
    assert resp.status_code == 201
    assert Assignment.objects_unscoped.filter(mission=mission, status="proposed").count() == 2


def test_propose_hard_blocked_user_rejected(auth_client_for):
    lead, mission = make_lead_mission()
    blocker = MissionFactory(tenant=lead.tenant, status=MissionStatus.ACTIVE,
                             start_date=D(2026, 9, 5), end_date=D(2026, 9, 15))
    busy = AssignmentFactory(mission=blocker, status=AssignmentStatus.ACCEPTED).user
    resp = auth_client_for(lead).post(f"/api/v1/missions/{mission.id}/assignments/",
                                      {"user_ids": [busy.id]}, format="json")
    assert resp.status_code == 400
    assert busy.name in resp.data["message"] or busy.name in str(resp.data["extra"])


def test_propose_beyond_max_crew_rejected(auth_client_for):
    lead, mission = make_lead_mission()  # max_crew=3
    crew = [UserFactory(role=Role.CREW_MEMBER, tenant=lead.tenant) for _ in range(4)]
    resp = auth_client_for(lead).post(f"/api/v1/missions/{mission.id}/assignments/",
                                      {"user_ids": [c.id for c in crew]}, format="json")
    assert resp.status_code == 400


def test_other_lead_cannot_manage(auth_client_for):
    _, mission = make_lead_mission()
    other_lead = UserFactory(role=Role.MISSION_LEAD, tenant=mission.tenant)
    crew = UserFactory(role=Role.CREW_MEMBER, tenant=mission.tenant)
    resp = auth_client_for(other_lead).post(f"/api/v1/missions/{mission.id}/assignments/",
                                            {"user_ids": [crew.id]}, format="json")
    assert resp.status_code == 403


def test_crew_accepts_and_declines_own_only(auth_client_for):
    assignment = AssignmentFactory()
    me_client = auth_client_for(assignment.user)
    resp = me_client.post(f"/api/v1/assignments/{assignment.id}/respond/", {"action": "accept"})
    assert resp.status_code == 200 and resp.data["status"] == "accepted"

    other = AssignmentFactory(mission=assignment.mission)
    resp = me_client.post(f"/api/v1/assignments/{other.id}/respond/", {"action": "accept"})
    assert resp.status_code == 403


def test_respond_twice_rejected(auth_client_for):
    assignment = AssignmentFactory(status=AssignmentStatus.ACCEPTED)
    resp = auth_client_for(assignment.user).post(
        f"/api/v1/assignments/{assignment.id}/respond/", {"action": "decline"})
    assert resp.status_code == 400


def test_my_assignments_nested_mission(auth_client_for):
    assignment = AssignmentFactory()
    resp = auth_client_for(assignment.user).get("/api/v1/me/assignments/")
    assert resp.status_code == 200
    assert resp.data["results"][0]["mission"]["name"] == assignment.mission.name


def test_staffing_endpoint_shape(auth_client_for):
    lead, mission = make_lead_mission()
    AssignmentFactory(mission=mission)
    resp = auth_client_for(lead).get(f"/api/v1/missions/{mission.id}/staffing/")
    assert resp.status_code == 200
    assert set(resp.data) >= {"requirements", "accepted_count", "min_crew", "max_crew",
                              "fully_covered", "roster"}
    assert resp.data["roster"][0]["status"] == "proposed"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/missions/test_assignment_apis.py -v` — Expected: FAIL.

- [ ] **Step 3: Implement**

`missions/services/assignments.py`:

```python
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from mission_control.common.exceptions import ApplicationError
from mission_control.missions.models import (
    Assignment, AssignmentStatus, LIVE_ASSIGNMENT_STATUSES, Mission, MissionStatus,
)
from mission_control.missions.selectors.staffing import hard_blocked_user_ids
from mission_control.missions.services.missions import _ensure_owns_or_director
from mission_control.tenants.context import require_current_tenant_id
from mission_control.users.models import User
from mission_control.users.roles import Role

TERMINAL = frozenset({MissionStatus.COMPLETED, MissionStatus.CANCELLED})


@transaction.atomic
def assignments_propose(*, actor, mission: Mission, user_ids: list[int]) -> list[Assignment]:
    _ensure_owns_or_director(actor, mission)
    if mission.status in TERMINAL:
        raise ApplicationError("Cannot assign crew to a completed or cancelled mission.")
    users = list(User.objects.filter(
        id__in=user_ids, tenant_id=require_current_tenant_id(),
        role=Role.CREW_MEMBER, is_active=True,
    ))
    if len(users) != len(set(user_ids)):
        raise ApplicationError("Some users are not assignable crew members.")
    already = set(Assignment.objects.filter(
        mission=mission, user_id__in=user_ids, status__in=LIVE_ASSIGNMENT_STATUSES,
    ).values_list("user_id", flat=True))
    if already:
        raise ApplicationError("Some crew already have a live assignment on this mission.")
    blocked = hard_blocked_user_ids(
        start_date=mission.start_date, end_date=mission.end_date, exclude_mission_id=mission.id,
    ) & {u.id for u in users}
    if blocked:
        names = ", ".join(u.name for u in users if u.id in blocked)
        raise ApplicationError(f"Unavailable for these dates: {names}.",
                               extra={"user_ids": sorted(blocked)})
    live_count = Assignment.objects.filter(
        mission=mission, status__in=LIVE_ASSIGNMENT_STATUSES).count()
    if live_count + len(users) > mission.max_crew:
        raise ApplicationError(f"This would exceed max_crew ({mission.max_crew}).")
    return Assignment.objects_unscoped.bulk_create([
        Assignment(tenant_id=require_current_tenant_id(), mission=mission,
                   user=u, created_by=actor)
        for u in users
    ])


def assignment_remove(*, actor, assignment: Assignment) -> Assignment:
    _ensure_owns_or_director(actor, assignment.mission)
    if assignment.status not in LIVE_ASSIGNMENT_STATUSES:
        raise ApplicationError("Only proposed or accepted assignments can be removed.")
    assignment.status = AssignmentStatus.REMOVED
    assignment.save(update_fields=["status", "updated_at"])
    return assignment


def assignment_respond(*, actor, assignment: Assignment, action: str, reason: str = "") -> Assignment:
    if assignment.user_id != actor.id:
        raise PermissionDenied("You can only respond to your own assignments.")
    if assignment.mission.status in TERMINAL:
        raise ApplicationError("This mission is no longer active.")
    if assignment.status != AssignmentStatus.PROPOSED:
        raise ApplicationError("This assignment has already been responded to.")
    if action == "accept":
        assignment.status = AssignmentStatus.ACCEPTED
    elif action == "decline":
        assignment.status = AssignmentStatus.DECLINED
        assignment.decline_reason = reason
    else:
        raise ApplicationError(f"Unknown action '{action}'.")
    assignment.responded_at = timezone.now()
    assignment.save(update_fields=["status", "decline_reason", "responded_at", "updated_at"])
    return assignment
```

Selector additions (`selectors/missions.py`): `my_assignments(user)` → `Assignment.objects.filter(user=user).select_related("mission").order_by("-created_at")`; `mission_assignments(mission)` → `Assignment.objects.filter(mission=mission, status__in=LIVE_ASSIGNMENT_STATUSES).select_related("user")`.

`missions/apis/assignments.py`: a shared `staffing_payload(mission)` helper builds the staffing dict from `mission_coverage` + roster (`mission_assignments` + `soft_conflicts_for_users` + `hard_blocked_user_ids`); views `MissionStaffingApi` (get), `MissionAssignmentsBulkApi` (post → 201), `AssignmentRemoveApi` (post), `MyAssignmentsApi` (get), `AssignmentRespondApi` (post) — each one `ensure_permission` + one service/selector call, assignment lookups via `get_object_or_404(Assignment.objects.select_related("mission", "user"), id=...)` (scoped manager → cross-tenant 404).

URLs: `missions/<int:mission_id>/staffing/`, `missions/<int:mission_id>/assignments/`, `assignments/<int:assignment_id>/remove/`, `assignments/<int:assignment_id>/respond/`, `me/assignments/`.

- [ ] **Step 4: Run tests, commit**

```bash
uv run pytest tests/ -v
git add -A && git commit -m "feat: assignment propose/remove/respond services and APIs, staffing endpoint"
```

---

### Task 4.4: Wire the staffing guard into the FSM

**Files:**
- Modify: `backend/mission_control/missions/services/missions.py` (replace `_validate_staffing_for_approval` body; extend `cancel`), `backend/tests/missions/test_fsm.py` (two Stage-3 tests approved unstaffed missions — legal then, not anymore; see Step 3b)
- Create: `backend/tests/missions/test_approval_guard.py`

**Interfaces:**
- Produces:
  - `_validate_staffing_for_approval(mission)` now: `select_for_update` on the mission's accepted crew's `User` rows (serializes competing approvals over shared people), then `staffing_validation_errors(mission)`; any errors → `ApplicationError("Mission staffing is not valid.", extra={"errors": [...]})`. Runs on **approve and activate** (already called at both sites).
  - `cancel` guard extension: after status write, live assignments flip to REMOVED (`Assignment.objects.filter(mission=mission, status__in=LIVE_ASSIGNMENT_STATUSES).update(status=AssignmentStatus.REMOVED)`).

- [ ] **Step 1: Write the failing tests**

`backend/tests/missions/test_approval_guard.py`:

```python
import datetime as dt

import pytest

from mission_control.common.exceptions import ApplicationError
from mission_control.missions.factories import (
    AssignmentFactory, MissionFactory, MissionRequirementFactory,
)
from mission_control.missions.models import Assignment, AssignmentStatus, MissionStatus
from mission_control.missions.services.missions import transition_mission
from mission_control.tenants.context import set_current_tenant_id
from mission_control.users.factories import CrewSkillFactory, SkillFactory, UserFactory
from mission_control.users.roles import Role

pytestmark = pytest.mark.django_db
D = dt.date


def staffed_pending_mission(**kwargs):
    mission = MissionFactory(start_date=D(2026, 9, 1), end_date=D(2026, 9, 10),
                             status=MissionStatus.PENDING_APPROVAL, **kwargs)
    set_current_tenant_id(mission.tenant_id)
    skill = SkillFactory(tenant=mission.tenant, name="Piloting")
    MissionRequirementFactory(mission=mission, skill=skill, min_proficiency=5)
    crew = UserFactory(role=Role.CREW_MEMBER, tenant=mission.tenant, name="Ada")
    CrewSkillFactory(user=crew, skill=skill, proficiency=8)
    AssignmentFactory(mission=mission, user=crew, status=AssignmentStatus.ACCEPTED)
    return mission, crew


def test_approve_succeeds_when_staffed():
    mission, _ = staffed_pending_mission()
    director = UserFactory(role=Role.DIRECTOR, tenant=mission.tenant)
    assert transition_mission(actor=director, mission=mission,
                              action="approve").status == MissionStatus.APPROVED


def test_approve_fails_without_coverage():
    mission, crew = staffed_pending_mission()
    Assignment.objects.filter(user=crew).update(status=AssignmentStatus.DECLINED)
    director = UserFactory(role=Role.DIRECTOR, tenant=mission.tenant)
    with pytest.raises(ApplicationError) as exc:
        transition_mission(actor=director, mission=mission, action="approve")
    assert "Piloting" in str(exc.value.extra["errors"])


def test_competing_approval_loses_shared_crew():
    mission_a, crew = staffed_pending_mission()
    director = UserFactory(role=Role.DIRECTOR, tenant=mission_a.tenant)
    # Mission B, same tenant, overlapping dates, same accepted crew member
    mission_b = MissionFactory(tenant=mission_a.tenant, status=MissionStatus.PENDING_APPROVAL,
                               start_date=D(2026, 9, 5), end_date=D(2026, 9, 15))
    skill_b = SkillFactory(tenant=mission_a.tenant, name="Navigation")
    MissionRequirementFactory(mission=mission_b, skill=skill_b, min_proficiency=1)
    CrewSkillFactory(user=crew, skill=skill_b, proficiency=5)
    AssignmentFactory(mission=mission_b, user=crew, status=AssignmentStatus.ACCEPTED)

    transition_mission(actor=director, mission=mission_a, action="approve")
    with pytest.raises(ApplicationError) as exc:
        transition_mission(actor=director, mission=mission_b, action="approve")
    assert "Ada" in str(exc.value.extra["errors"])


def test_cancel_removes_live_assignments():
    mission, crew = staffed_pending_mission()
    transition_mission(actor=mission.created_by, mission=mission, action="cancel", reason="Scrubbed")
    assignment = Assignment.objects.get(user=crew)
    assert assignment.status == AssignmentStatus.REMOVED
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/missions/test_approval_guard.py -v` — Expected: `test_approve_fails_without_coverage`, `test_competing_approval_loses_shared_crew`, `test_cancel_removes_live_assignments` FAIL (guard is a no-op; cancel doesn't touch assignments).

- [ ] **Step 3: Implement** in `services/missions.py`:

```python
def _validate_staffing_for_approval(mission):
    from mission_control.missions.models import Assignment, AssignmentStatus
    from mission_control.missions.selectors.staffing import staffing_validation_errors
    from mission_control.users.models import User

    accepted_user_ids = list(Assignment.objects.filter(
        mission=mission, status=AssignmentStatus.ACCEPTED).values_list("user_id", flat=True))
    # Serialize competing approvals that share crew members.
    list(User.objects.select_for_update().filter(id__in=accepted_user_ids))
    errors = staffing_validation_errors(mission)
    if errors:
        raise ApplicationError("Mission staffing is not valid.", extra={"errors": errors})
```

And at the end of `transition_mission`, after the status write:

```python
    if action == "cancel":
        from mission_control.missions.models import Assignment, AssignmentStatus, LIVE_ASSIGNMENT_STATUSES
        Assignment.objects.filter(mission=mission, status__in=LIVE_ASSIGNMENT_STATUSES) \
            .update(status=AssignmentStatus.REMOVED)
```

(Local imports keep `services/missions.py` free of an import cycle with the staffing selector.)

- [ ] **Step 3b: Update the two Stage-3 FSM tests that now need staffed missions**

In `backend/tests/missions/test_fsm.py`, add a helper that staffs the fixture mission, and use it in `test_happy_path_submit_approve` and `test_activate_needs_start_date_reached` before the approve step:

```python
from mission_control.missions.factories import AssignmentFactory
from mission_control.missions.models import AssignmentStatus
from mission_control.users.factories import CrewSkillFactory


def staff(mission):
    """Accept one qualified crew member so the staffing guard passes (requirement is prof>=5)."""
    requirement = mission.requirements.first()
    crew = UserFactory(role=Role.CREW_MEMBER, tenant=mission.tenant)
    CrewSkillFactory(user=crew, skill=requirement.skill, proficiency=requirement.min_proficiency)
    AssignmentFactory(mission=mission, user=crew, status=AssignmentStatus.ACCEPTED)
```

Call `staff(mission)` right after obtaining the mission in both tests (before `submit`). The other FSM tests intentionally never reach a staffing-validated transition and stay untouched.

- [ ] **Step 4: Run the full suite, commit**

```bash
uv run pytest tests/ -v
git add -A && git commit -m "feat: approve/activate staffing guard with crew-row locking; cancel removes live assignments"
```

---

### Task 4.5: Frontend — staffing panel

**Files:**
- Create: `frontend/src/features/assignments/api/assignments.ts`, `frontend/src/features/assignments/components/{staffing-panel.tsx,add-crew-dialog.tsx}`, `frontend/src/features/assignments/staffing.test.tsx`
- Modify: `frontend/src/features/missions/components/mission-detail-page.tsx` (replace Staffing placeholder), `frontend/src/testing/mocks.ts`

**Interfaces:**
- Produces:
  - `features/assignments/api/assignments.ts`: `StaffingSchema` (mirror of the staffing payload), `useStaffing(missionId)` (key `["missions", missionId, "staffing"]`), `useProposeAssignments(missionId)`, `useRemoveAssignment(missionId)` — mutations invalidate the staffing key and `["missions", missionId]`; `MyAssignmentSchema` + `useMyAssignments()` + `useRespondAssignment()` (used by Task 4.6)
  - `staffing-panel.tsx`: per requirement a coverage row — "Piloting ≥7 · 1/2" with a progress bar and the filler names; roster list (name, assignment status badge, amber "conflict" chip with popover listing soft conflicts, red "unavailable" chip when `hard_blocked`); remove button per row (when `assignment.manage`); "Add crew" button → `add-crew-dialog` (multi-select from `useCrew()`, excludes current roster) — visible only with `assignment.manage`
- Consumes: `useCrew` (Stage 2), mission detail page section slot

- [ ] **Step 1: Write the failing test** — `staffing.test.tsx`: mock `GET /api/v1/missions/10/staffing/` with one requirement `{skill_name: "Piloting", min_proficiency: 7, required_count: 2, filled_count: 1, filled_by: [...]}` and a roster of two (one with a soft conflict); render `/missions/10`; assert "1/2" and the conflict chip appear; click remove on a roster row and assert `POST .../remove/` was called (msw spy). Run: `npm test -- --run` — Expected: FAIL.

- [ ] **Step 2: Implement** per Interfaces (coverage bar = shadcn-styled div with width %; conflicts in `Popover`).

- [ ] **Step 3: Verify green, commit**

```bash
npm test -- --run && npm run build
git add -A && git commit -m "feat: staffing panel with coverage bars, conflict chips, crew management"
```

---

### Task 4.6: Frontend — my assignments

**Files:**
- Create: `frontend/src/features/assignments/components/my-assignments-page.tsx`, `frontend/src/features/assignments/my-assignments.test.tsx`
- Modify: `frontend/src/app/router.tsx` (replace placeholder)

**Interfaces:**
- Produces: `/my-assignments` (gated `assignment.respond`): three groups — **Pending proposals** (cards: mission name, dates, description; Accept button; Decline button opening a small dialog with optional reason), **Upcoming** (accepted, mission not completed/cancelled), **History** (everything else, muted). Empty states for each group ("No pending proposals").
- Consumes: `useMyAssignments`, `useRespondAssignment` from Task 4.5

- [ ] **Step 1: Write the failing test** — render `/my-assignments` as `crewUser` with one proposed + one accepted fixture; accept the proposal; assert `POST /api/v1/assignments/1/respond/` body `{action: "accept"}` and the card moves after invalidation (mock returns accepted). Run: `npm test -- --run` — Expected: FAIL.

- [ ] **Step 2: Implement** per Interfaces.

- [ ] **Step 3: Verify green + manual smoke, commit**

Manual (dev compose): lead proposes crew on a draft mission → crew logs in, accepts → lead sees coverage fill in → submit → director approve succeeds; decline path shows reason to the lead in the roster popover.

```bash
npm test -- --run && npm run build
git add -A && git commit -m "feat: my-assignments page with accept/decline flows"
```

---

**Stage 4 exit criteria:** suites green · propose→accept→approve happy path works end-to-end in UI · approve fails with actionable errors when under-staffed or double-booked · competing approval test proves first-approved-wins · cancel clears live assignments.
