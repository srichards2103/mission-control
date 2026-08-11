from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

from mission_control.common.models import BaseModel
from mission_control.tenants.models import TenantModel
from mission_control.users.roles import Role


class UserManager(BaseUserManager):
    def create_user(self, *, email, password, tenant, role, name):
        user = self.model(email=self.normalize_email(email), tenant=tenant, role=role, name=name)
        user.set_password(password)
        user.save()
        return user


class User(AbstractBaseUser, BaseModel):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT, related_name="users")
    role = models.CharField(max_length=32, choices=Role.choices)
    is_active = models.BooleanField(default=True)

    objects = UserManager()  # standard manager: auth resolves users before tenant context exists

    USERNAME_FIELD = "email"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "id"], name="users_user_tenant_id_uniq"),
        ]

    def __str__(self):
        return self.email


class Skill(TenantModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_archived = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("name"), "tenant", name="skill_name_per_tenant_uniq"),
            models.UniqueConstraint(fields=["tenant", "id"], name="skill_tenant_id_uniq"),
        ]

    def __str__(self):
        return self.name


class CrewSkill(TenantModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="crew_skills")
    skill = models.ForeignKey(Skill, on_delete=models.PROTECT, related_name="crew_skills")
    proficiency = models.PositiveSmallIntegerField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(proficiency__gte=1) & Q(proficiency__lte=10),
                name="crewskill_proficiency_1_10",
            ),
            models.UniqueConstraint(fields=["user", "skill"], name="crewskill_user_skill_uniq"),
        ]
