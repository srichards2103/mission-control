from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models

from mission_control.common.models import BaseModel
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
