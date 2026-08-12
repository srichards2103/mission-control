from django.db import transaction

from mission_control.common.db import integrity_error_as
from mission_control.common.exceptions import ApplicationError
from mission_control.tenants.context import require_current_tenant_id
from mission_control.users.models import SKILL_NAME_TAKEN, CrewSkill, Skill, User

EMAIL_TAKEN = "A user with this email already exists."


def skill_create(*, actor, name: str, description: str = "") -> Skill:
    # Stamp tenant before full_clean: excluding it would skip the (tenant, lower(name))
    # unique validation and turn duplicate names into 500s instead of 400s.
    skill = Skill(name=name, description=description, tenant_id=require_current_tenant_id())
    skill.full_clean()
    # full_clean's validate_constraints() is a non-locking SELECT; see
    # `integrity_error_as` for why the INSERT still needs its own guard, and why the
    # message it raises is the one the sequential path produces.
    with integrity_error_as("Validation error", {"fields": {"__all__": [SKILL_NAME_TAKEN]}}):
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
    CrewSkill.objects.bulk_create([
        CrewSkill(tenant_id=require_current_tenant_id(), user=actor,
                  skill_id=item["skill_id"], proficiency=item["proficiency"])
        for item in items
    ])


def user_create(*, actor, email: str, name: str, role: str, password: str) -> User:
    # `email` is globally unique (User is not tenant-scoped), so this existence check
    # must run across ALL tenants, not just the current one -- that's deliberate, not a
    # tenancy leak: it only prevents an IntegrityError, it returns no other tenant's data.
    # Checked explicitly (rather than relying on full_clean()'s validate_unique, which is
    # case-sensitive) so a same-address-different-case collision also surfaces as the
    # standard {"message": "Validation error", "extra": {"fields": {...}}} 400 envelope
    # instead of a raw IntegrityError 500.
    duplicate = {"fields": {"email": [EMAIL_TAKEN]}}
    if User.objects.filter(email__iexact=email).exists():
        raise ApplicationError("Validation error", extra=duplicate)
    # The check above is a non-locking SELECT, so a concurrent create of the same
    # address still loses the race at the INSERT; report it identically.
    with integrity_error_as("Validation error", duplicate):
        user = User.objects.create_user(
            email=email, password=password, tenant=actor.tenant, role=role, name=name
        )
    return user


def user_update(
    *, actor, user: User, role: str | None = None, is_active: bool | None = None
) -> User:
    if user == actor:
        raise ApplicationError("You cannot change your own account.")
    if role is not None:
        user.role = role
    if is_active is not None:
        user.is_active = is_active
    user.full_clean()
    user.save()
    return user
