from django.shortcuts import get_object_or_404

from mission_control.tenants.context import require_current_tenant_id
from mission_control.users.models import CrewSkill, Skill, User
from mission_control.users.roles import Role


def skill_list():
    return Skill.objects.order_by("is_archived", "name")


def skill_get(skill_id: int) -> Skill:
    return get_object_or_404(Skill, id=skill_id)


def crew_skills_for_user(user):
    return CrewSkill.objects.filter(user=user).select_related("skill").order_by("skill__name")


def crew_list():
    return (
        User.objects.filter(
            tenant_id=require_current_tenant_id(), role=Role.CREW_MEMBER, is_active=True
        )
        .prefetch_related("crew_skills__skill")
        .order_by("name")
    )


def crew_get(user_id: int) -> User:
    return get_object_or_404(crew_list(), id=user_id)
