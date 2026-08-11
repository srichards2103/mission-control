from django.db import transaction

from mission_control.common.exceptions import ApplicationError
from mission_control.tenants.context import require_current_tenant_id
from mission_control.users.models import CrewSkill, Skill


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
