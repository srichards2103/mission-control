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
    """Base for every tenant-scoped model: `objects` is filtered, `save()` stamps.

    `objects` (a `TenantManager`) filters by the tenant in context and raises
    `TenantContextNotSet` when there is none, so a query written without thinking about
    tenancy fails closed rather than returning another organisation's rows. `save()`
    stamps `tenant_id` from the same context when it isn't already set.

    Two footguns, both of which bypass that protection:

    * **`objects_unscoped` is for migrations and test fixtures only.** It is the plain
      manager -- no tenant filter, no `TenantContextNotSet`. It exists because data
      migrations and factories legitimately need to touch several tenants at once (see
      `tenants.factories.TenantModelFactory`). Application code must never use it; the
      404-not-403 cross-tenant contract depends on `objects`.
    * **`bulk_create` / `bulk_update` do not call `save()`,** so they skip the tenant
      stamping above. Every row handed to them must already carry an explicit
      `tenant_id` (as `users.services.crew_skills_set` and
      `missions.services.missions.mission_requirements_set` do). They also skip
      `full_clean()`, so validate rows yourself if you need the 400 envelope rather
      than an `IntegrityError`.

    Neither rule is enforceable in Python, which is why every tenant-coherence
    invariant is additionally a database constraint (`UNIQUE(tenant_id, id)` plus
    composite FKs) -- see the project's tenancy-hardening notes.
    """

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
