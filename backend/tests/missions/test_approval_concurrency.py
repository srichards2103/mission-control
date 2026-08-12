"""Two competing approvals over shared crew: exactly one succeeds (spec §14).

The existing approval-guard tests approve mission A to completion and only *then*
attempt B, which is purely sequential -- it would pass with no locking at all, so it
does not exercise `_lock_accepted_crew`, whose whole reason to exist is this race.

This test runs the two approvals on two real connections at once. Both missions are
independently valid at the moment the threads start; the only thing that can make one
of them invalid is the other committing first. Without the row lock both transactions
read each other's pre-commit state, both pass the conflict check, and Ada ends up
accepted on two overlapping approved missions -- the state `matching._committed_days`
and `crew_utilization` both assume impossible. With it, the second transaction blocks
on Ada's `User` row until the first commits, then sees the conflict it created.

`transaction=True` (a real TransactionTestCase) is required: the usual test transaction
would keep each thread's writes invisible to the other, which is exactly the thing under
test. Each thread manages its own connection and its own tenant context, since both are
thread-local.
"""

import datetime as dt
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.db import close_old_connections

from mission_control.common.exceptions import ApplicationError
from mission_control.missions.factories import (
    AssignmentFactory,
    MissionFactory,
    MissionRequirementFactory,
)
from mission_control.missions.models import AssignmentStatus, Mission, MissionStatus
from mission_control.missions.selectors.staffing import hard_blocked_user_ids
from mission_control.missions.services.missions import transition_mission
from mission_control.tenants.context import set_current_tenant_id
from mission_control.users.factories import (
    CrewSkillFactory,
    SkillFactory,
    TenantFactory,
    UserFactory,
)
from mission_control.users.roles import Role

D = dt.date


@pytest.mark.django_db(transaction=True)
def test_two_competing_approvals_over_shared_crew_leave_exactly_one_approved():
    tenant = TenantFactory()
    set_current_tenant_id(tenant.id)
    skill = SkillFactory(tenant=tenant, name="Piloting")
    ada = UserFactory(role=Role.CREW_MEMBER, tenant=tenant, name="Ada")
    CrewSkillFactory(user=ada, skill=skill, proficiency=9)
    lead = UserFactory(role=Role.MISSION_LEAD, tenant=tenant)
    director = UserFactory(role=Role.DIRECTOR, tenant=tenant)

    missions = []
    for name, start in (("Alpha", D(2026, 9, 1)), ("Bravo", D(2026, 9, 5))):
        mission = MissionFactory(
            tenant=tenant, created_by=lead, name=name, status=MissionStatus.PENDING_APPROVAL,
            start_date=start, end_date=start + dt.timedelta(days=9), min_crew=1, max_crew=2,
        )
        MissionRequirementFactory(
            mission=mission, skill=skill, min_proficiency=5, required_count=1
        )
        AssignmentFactory(
            mission=mission, user=ada, status=AssignmentStatus.ACCEPTED, tenant=tenant
        )
        missions.append(mission)

    start_together = Barrier(len(missions), timeout=10)

    def approve(mission_id):
        close_old_connections()
        set_current_tenant_id(tenant.id)
        try:
            mission = Mission.objects.get(id=mission_id)
            start_together.wait()
            transition_mission(actor=director, mission=mission, action="approve")
            return "approved"
        except ApplicationError:
            return "rejected"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=len(missions)) as pool:
        outcomes = sorted(pool.map(approve, [m.id for m in missions]))

    assert outcomes == ["approved", "rejected"]

    set_current_tenant_id(tenant.id)
    statuses = sorted(Mission.objects.values_list("status", flat=True))
    assert statuses == [MissionStatus.APPROVED, MissionStatus.PENDING_APPROVAL]
    # And the DB is consistent with the availability rule: Ada is committed to exactly
    # one of the two windows, not both.
    blocked_windows = [
        m
        for m in missions
        if ada.id
        in hard_blocked_user_ids(start_date=m.start_date, end_date=m.end_date)
    ]
    assert len(blocked_windows) == 2  # both windows overlap the single approved mission
    approved = Mission.objects.get(status=MissionStatus.APPROVED)
    assert (
        Mission.objects.filter(
            assignments__user=ada,
            assignments__status=AssignmentStatus.ACCEPTED,
            status__in=[MissionStatus.APPROVED, MissionStatus.ACTIVE],
        ).count()
        == 1
    )
    assert approved.id in {m.id for m in missions}
