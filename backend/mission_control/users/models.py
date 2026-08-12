from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

from mission_control.common.models import BaseModel
from mission_control.tenants.models import TenantModel
from mission_control.users.roles import Role


class UserManager(BaseUserManager):
    @staticmethod
    def normalize_email(email):
        """Lowercase the WHOLE address, not just the domain.

        Django's `BaseUserManager.normalize_email` lowercases only the domain part, so
        a director hand-entering `Sam@example.com` stored a row that `sam@example.com`
        could never find again: login is an exact match on `USERNAME_FIELD`,
        `user_create`'s `email__iexact` guard then refuses to create the lowercase
        variant, `user_update` accepts only `role`/`is_active`, and there is no
        email-change or password-reset flow -- the account is unusable and
        unrepairable through the product. Addresses are stored in one canonical form
        instead.
        """
        return BaseUserManager.normalize_email(email).lower()

    def get_by_natural_key(self, username):
        # Stored addresses are canonically lowercase (above), but a human typing their
        # own email at the login form is under no such discipline. `iexact` so
        # `Sam@example.com` authenticates against the stored `sam@example.com` instead
        # of failing with "no active account found".
        return self.get(**{f"{self.model.USERNAME_FIELD}__iexact": username})

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
            models.UniqueConstraint(
                fields=["tenant", "id"],
                name="users_user_tenant_id_uniq",
                violation_error_message="This user does not belong to that organisation.",
            ),
        ]

    def __str__(self):
        return self.email


class Skill(TenantModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_archived = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                "tenant",
                name="skill_name_per_tenant_uniq",
                violation_error_message="A skill with this name already exists.",
            ),
            models.UniqueConstraint(
                fields=["tenant", "id"],
                name="skill_tenant_id_uniq",
                violation_error_message="This skill does not belong to that organisation.",
            ),
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
                violation_error_message="Proficiency must be between 1 and 10.",
            ),
            models.UniqueConstraint(
                fields=["user", "skill"],
                name="crewskill_user_skill_uniq",
                violation_error_message="This skill is already listed on the profile.",
            ),
        ]
