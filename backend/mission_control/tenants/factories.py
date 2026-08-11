import factory


class TenantModelFactory(factory.django.DjangoModelFactory):
    """Base for factories building `TenantModel` subclasses.

    Tenant is always supplied explicitly to these factories (directly or via a
    SubFactory/SelfAttribute chain), so route creation through the unscoped manager
    rather than forcing every caller to push a tenant into context just to build
    fixtures (e.g. cross-tenant test setup). This bypasses only the Python-level
    `WHERE tenant_id = ...` filter on create — no database constraint is skipped.
    """

    class Meta:
        abstract = True

    @classmethod
    def _get_manager(cls, model_class):
        return model_class.objects_unscoped
