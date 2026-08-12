import datetime as dt

import pytest
from django.db import IntegrityError, transaction

from mission_control.missions.factories import MissionFactory, MissionRequirementFactory
from mission_control.missions.models import MissionRequirement, MissionStatus
from mission_control.users.factories import SkillFactory, TenantFactory

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


def test_mission_factory_created_by_same_tenant():
    mission = MissionFactory()
    assert mission.created_by.tenant_id == mission.tenant_id


def test_requirement_factory_keeps_tenant_consistent():
    requirement = MissionRequirementFactory()
    assert requirement.tenant_id == requirement.mission.tenant_id == requirement.skill.tenant_id


def test_requirement_proficiency_bounds_check():
    with pytest.raises(IntegrityError):
        MissionRequirementFactory(min_proficiency=11)


def test_requirement_count_bounds_check():
    with pytest.raises(IntegrityError):
        MissionRequirementFactory(required_count=0)


def test_requirement_unique_mission_skill_proficiency():
    mission = MissionFactory()
    skill = SkillFactory(tenant=mission.tenant)
    MissionRequirementFactory(
        mission=mission, tenant=mission.tenant, skill=skill, min_proficiency=5
    )
    with pytest.raises(IntegrityError):
        MissionRequirementFactory(
            mission=mission, tenant=mission.tenant, skill=skill, min_proficiency=5
        )


def test_composite_fk_blocks_cross_tenant_mission():
    t1, t2 = TenantFactory(), TenantFactory()
    mission_t1 = MissionFactory(tenant=t1)
    skill_t2 = SkillFactory(tenant=t2)
    with pytest.raises(IntegrityError) as excinfo:
        with transaction.atomic():
            MissionRequirement.objects_unscoped.create(
                tenant=t2, mission=mission_t1, skill=skill_t2, min_proficiency=5, required_count=1
            )
    assert "requirement_tenant_mission_fk" in str(excinfo.value)


def test_composite_fk_blocks_cross_tenant_skill():
    t1, t2 = TenantFactory(), TenantFactory()
    mission_t1 = MissionFactory(tenant=t1)
    skill_t2 = SkillFactory(tenant=t2)
    with pytest.raises(IntegrityError) as excinfo:
        with transaction.atomic():
            MissionRequirement.objects_unscoped.create(
                tenant=t1, mission=mission_t1, skill=skill_t2, min_proficiency=5, required_count=1
            )
    assert "requirement_tenant_skill_fk" in str(excinfo.value)
