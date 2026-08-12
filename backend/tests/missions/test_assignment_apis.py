import datetime as dt

import pytest
from django.core.exceptions import ValidationError as DjangoValidationError

from mission_control.missions.factories import AssignmentFactory, MissionFactory
from mission_control.missions.models import Assignment, AssignmentStatus, MissionStatus
from mission_control.tenants.context import set_current_tenant_id
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


# --------------------------------------------------------------------------- additional coverage
# The rest of this file goes beyond the brief's Step-1 sample to close gaps flagged by the
# task's self-review checklist: the global list-envelope ruling, cross-tenant 404s, the
# partial-unique-constraint-as-400 requirement, decline reasons, and removal.


def test_my_assignments_uses_standard_paginated_envelope(auth_client_for):
    """Ruling 2: /me/assignments/ uses {results, count, limit, offset}, not a bare list."""
    assignment = AssignmentFactory()
    resp = auth_client_for(assignment.user).get("/api/v1/me/assignments/")
    assert resp.status_code == 200
    assert set(resp.data) == {"results", "count", "limit", "offset"}
    assert resp.data["count"] == 1


def test_propose_duplicate_live_assignment_rejected_cleanly(auth_client_for):
    """A second live proposal for the same (mission, user) must be a 400, never a 500.

    `assignments_propose` pre-checks this with an explicit query, but the service also
    calls `full_clean()` (not `bulk_create`) before every save, so the partial
    `assignment_live_uniq` constraint is defense-in-depth: even if the pre-check were
    ever removed, Django's `validate_constraints()` converts the conditional unique
    violation into a `ValidationError`, which the global exception handler renders as
    the standard 400 envelope rather than surfacing an `IntegrityError` as a 500.
    """
    lead, mission = make_lead_mission()
    crew = UserFactory(role=Role.CREW_MEMBER, tenant=lead.tenant)
    client = auth_client_for(lead)
    url = f"/api/v1/missions/{mission.id}/assignments/"
    first = client.post(url, {"user_ids": [crew.id]}, format="json")
    assert first.status_code == 201

    second = client.post(url, {"user_ids": [crew.id]}, format="json")
    assert second.status_code == 400
    assert second.data["message"] != "Validation error" or "fields" in second.data["extra"]
    assert Assignment.objects_unscoped.filter(mission=mission, user=crew).count() == 1


def test_full_clean_rejects_duplicate_live_assignment_as_validation_error_not_integrity_error():
    """Model-level proof that the partial `assignment_live_uniq` constraint is caught by
    `full_clean()`'s `validate_constraints()` step, independent of any service-level pre-check.
    """
    existing = AssignmentFactory(status=AssignmentStatus.PROPOSED)
    set_current_tenant_id(existing.tenant_id)
    dup = Assignment(
        tenant_id=existing.tenant_id,
        mission=existing.mission,
        user=existing.user,
        created_by=existing.created_by,
    )
    with pytest.raises(DjangoValidationError):
        dup.full_clean()


def test_reproposing_after_removal_is_permitted_via_api(auth_client_for):
    lead, mission = make_lead_mission()
    crew = UserFactory(role=Role.CREW_MEMBER, tenant=lead.tenant)
    client = auth_client_for(lead)
    url = f"/api/v1/missions/{mission.id}/assignments/"
    resp = client.post(url, {"user_ids": [crew.id]}, format="json")
    assert resp.status_code == 201
    assignment = Assignment.objects_unscoped.get(mission=mission, user=crew)

    remove_resp = client.post(f"/api/v1/assignments/{assignment.id}/remove/")
    assert remove_resp.status_code == 200
    assignment.refresh_from_db()
    assert assignment.status == AssignmentStatus.REMOVED

    resp = client.post(url, {"user_ids": [crew.id]}, format="json")
    assert resp.status_code == 201
    assert Assignment.objects_unscoped.filter(
        mission=mission, user=crew, status="proposed"
    ).count() == 1


def test_decline_sets_reason_and_responded_at(auth_client_for):
    assignment = AssignmentFactory()
    resp = auth_client_for(assignment.user).post(
        f"/api/v1/assignments/{assignment.id}/respond/",
        {"action": "decline", "reason": "Scheduling conflict"},
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "declined"
    assert resp.data["decline_reason"] == "Scheduling conflict"
    assert resp.data["responded_at"] is not None
    assignment.refresh_from_db()
    assert assignment.status == AssignmentStatus.DECLINED
    assert assignment.decline_reason == "Scheduling conflict"
    assert assignment.responded_at is not None


def test_remove_persists_and_is_idempotent_guarded(auth_client_for):
    lead, mission = make_lead_mission()
    assignment = AssignmentFactory(mission=mission, created_by=lead)
    client = auth_client_for(lead)

    resp = client.post(f"/api/v1/assignments/{assignment.id}/remove/")
    assert resp.status_code == 200
    assignment.refresh_from_db()
    assert assignment.status == AssignmentStatus.REMOVED

    again = client.post(f"/api/v1/assignments/{assignment.id}/remove/")
    assert again.status_code == 400


def test_cross_tenant_assignment_respond_404(auth_client_for):
    # Must be a crew member to hold `assignment.respond` at all, so the 404 below is
    # genuinely about tenant scoping, not a 403 from lacking the permission.
    crew = UserFactory(role=Role.CREW_MEMBER)
    other = AssignmentFactory()  # different tenant
    resp = auth_client_for(crew).post(
        f"/api/v1/assignments/{other.id}/respond/", {"action": "accept"}
    )
    assert resp.status_code == 404


def test_cross_tenant_staffing_404(auth_client_for):
    lead = UserFactory(role=Role.MISSION_LEAD)
    other_mission = MissionFactory()  # different tenant
    resp = auth_client_for(lead).get(f"/api/v1/missions/{other_mission.id}/staffing/")
    assert resp.status_code == 404


def test_crew_cannot_manage_assignments(auth_client_for):
    lead, mission = make_lead_mission()
    crew_mgr = UserFactory(role=Role.CREW_MEMBER, tenant=lead.tenant)
    other = UserFactory(role=Role.CREW_MEMBER, tenant=lead.tenant)
    resp = auth_client_for(crew_mgr).post(
        f"/api/v1/missions/{mission.id}/assignments/", {"user_ids": [other.id]}, format="json"
    )
    assert resp.status_code == 403


def test_propose_inactive_user_rejected(auth_client_for):
    lead, mission = make_lead_mission()
    inactive = UserFactory(role=Role.CREW_MEMBER, tenant=lead.tenant, is_active=False)
    resp = auth_client_for(lead).post(
        f"/api/v1/missions/{mission.id}/assignments/", {"user_ids": [inactive.id]}, format="json"
    )
    assert resp.status_code == 400


def test_staffing_roster_reflects_soft_conflict_and_hard_block(auth_client_for):
    lead, mission = make_lead_mission()
    soft_mission = MissionFactory(
        tenant=lead.tenant, status=MissionStatus.DRAFT,
        start_date=D(2026, 9, 5), end_date=D(2026, 9, 15),
    )
    conflicted = AssignmentFactory(mission=mission, status=AssignmentStatus.PROPOSED)
    AssignmentFactory(mission=soft_mission, user=conflicted.user, status=AssignmentStatus.PROPOSED)

    resp = auth_client_for(lead).get(f"/api/v1/missions/{mission.id}/staffing/")
    assert resp.status_code == 200
    roster_row = next(r for r in resp.data["roster"] if r["user_id"] == conflicted.user_id)
    assert roster_row["hard_blocked"] is False
    assert len(roster_row["soft_conflicts"]) == 1
    assert roster_row["soft_conflicts"][0]["mission_id"] == soft_mission.id
