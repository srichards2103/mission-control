from django.db import models

from mission_control.common.models import BaseModel
from mission_control.tenants.context import require_current_tenant_id


class Tenant(BaseModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=64, unique=True)

    def __str__(self):
        return self.slug


class TenantManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(tenant_id=require_current_tenant_id())


class TenantModel(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, related_name="+")

    objects = TenantManager()
    objects_unscoped = models.Manager()

    class Meta:
        abstract = True
        base_manager_name = "objects_unscoped"

    def save(self, *args, **kwargs):
        if self.tenant_id is None:
            self.tenant_id = require_current_tenant_id()
        super().save(*args, **kwargs)
