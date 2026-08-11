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
