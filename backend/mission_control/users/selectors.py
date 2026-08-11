from django.shortcuts import get_object_or_404

from mission_control.users.models import Skill


def skill_list():
    return Skill.objects.order_by("is_archived", "name")


def skill_get(skill_id: int) -> Skill:
    return get_object_or_404(Skill, id=skill_id)
