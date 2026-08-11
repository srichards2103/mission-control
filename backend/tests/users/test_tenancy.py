import pytest
from django.db import IntegrityError

from mission_control.tenants.context import TenantContextNotSet, set_current_tenant_id
from mission_control.users.factories import (
    CrewSkillFactory,
    SkillFactory,
    TenantFactory,
    UserFactory,
)
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
    with pytest.raises(IntegrityError) as excinfo:
        CrewSkill.objects_unscoped.create(tenant=t2, user=user_t1, skill=skill_t2, proficiency=5)
    assert "crewskill_tenant_user_fk" in str(excinfo.value)


def test_composite_fk_blocks_cross_tenant_skill():
    t1, t2 = TenantFactory(), TenantFactory()
    user_t1 = UserFactory(tenant=t1)
    skill_t2 = SkillFactory(tenant=t2)
    with pytest.raises(IntegrityError) as excinfo:
        CrewSkill.objects_unscoped.create(tenant=t1, user=user_t1, skill=skill_t2, proficiency=5)
    assert "crewskill_tenant_skill_fk" in str(excinfo.value)


def test_crewskill_factory_keeps_tenant_consistent():
    cs = CrewSkillFactory()
    assert cs.tenant_id == cs.user.tenant_id == cs.skill.tenant_id


def test_proficiency_check_constraint():
    user = UserFactory()
    skill = SkillFactory(tenant=user.tenant)
    with pytest.raises(IntegrityError):
        CrewSkill.objects_unscoped.create(
            tenant=user.tenant, user=user, skill=skill, proficiency=11
        )
