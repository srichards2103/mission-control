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
