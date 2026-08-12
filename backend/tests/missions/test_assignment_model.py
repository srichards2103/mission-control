import pytest
from django.db import IntegrityError, transaction

from mission_control.missions.factories import AssignmentFactory, MissionFactory
from mission_control.missions.models import Assignment, AssignmentStatus
from mission_control.users.factories import TenantFactory, UserFactory

pytestmark = pytest.mark.django_db


def test_second_live_assignment_for_same_pair_blocked():
    a = AssignmentFactory(status=AssignmentStatus.ACCEPTED)
    with pytest.raises(IntegrityError):
        AssignmentFactory(mission=a.mission, user=a.user, status=AssignmentStatus.PROPOSED)


def test_reproposing_after_decline_is_allowed():
    a = AssignmentFactory(status=AssignmentStatus.DECLINED)
    again = AssignmentFactory(mission=a.mission, user=a.user)  # proposed
    assert again.pk != a.pk


def test_assignment_factory_keeps_tenant_consistent():
    a = AssignmentFactory()
    assert a.tenant_id == a.mission.tenant_id == a.user.tenant_id == a.created_by.tenant_id


def test_composite_fk_blocks_cross_tenant_mission():
    t1, t2 = TenantFactory(), TenantFactory()
    mission_t1 = MissionFactory(tenant=t1)
    user_t2 = UserFactory(tenant=t2)
    with pytest.raises(IntegrityError) as excinfo:
        with transaction.atomic():
            Assignment.objects_unscoped.create(
                tenant=t2, mission=mission_t1, user=user_t2, created_by=user_t2
            )
    assert "assignment_tenant_mission_fk" in str(excinfo.value)


def test_composite_fk_blocks_cross_tenant_user():
    t1, t2 = TenantFactory(), TenantFactory()
    mission_t1 = MissionFactory(tenant=t1)
    user_t2 = UserFactory(tenant=t2)
    with pytest.raises(IntegrityError) as excinfo:
        with transaction.atomic():
            Assignment.objects_unscoped.create(
                tenant=t1, mission=mission_t1, user=user_t2, created_by=mission_t1.created_by
            )
    assert "assignment_tenant_user_fk" in str(excinfo.value)


# --- Obligation from Task 4.1's review -----------------------------------------------
#
# `Assignment.mission`/`Assignment.user` are Django `on_delete=CASCADE`, but the
# SQL-level composite tenant FKs (`assignment_tenant_mission_fk`,
# `assignment_tenant_user_fk`) are plain `NO ACTION`. The reviewer judged this
# mechanically sound -- Django's delete collector removes the dependent `Assignment`
# rows in the same transaction *before* the `Mission`/`User` row they reference, so by
# the time the composite FK's per-statement check runs against the parent row, no
# Assignment row still points at it -- but flagged that nothing exercised it. These two
# prove a real deletion goes through without an unhandled `IntegrityError`.


def test_deleting_mission_cascades_its_assignments():
    a = AssignmentFactory(status=AssignmentStatus.ACCEPTED)
    mission, assignment_id = a.mission, a.id
    mission.delete()
    assert not Assignment.objects_unscoped.filter(id=assignment_id).exists()


def test_deleting_user_cascades_their_assignments():
    a = AssignmentFactory(status=AssignmentStatus.ACCEPTED)
    user, assignment_id = a.user, a.id
    # `user` here only ever appears as the assignment's crew member -- never as
    # `created_by` on a Mission/Assignment (those are PROTECT) -- so this exercises
    # the CASCADE path cleanly rather than tripping a PROTECT first.
    user.delete()
    assert not Assignment.objects_unscoped.filter(id=assignment_id).exists()
