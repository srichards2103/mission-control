import factory

from mission_control.tenants.models import Tenant
from mission_control.users.models import CrewSkill, Skill, User
from mission_control.users.roles import Role


class TenantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tenant

    name = factory.Sequence(lambda n: f"Tenant {n}")
    slug = factory.Sequence(lambda n: f"tenant-{n}")


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    name = factory.Sequence(lambda n: f"User {n}")
    tenant = factory.SubFactory(TenantFactory)
    role = Role.CREW_MEMBER

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        # Custom hook (rather than factory.PostGenerationMethodCall) so the save that
        # persists the hashed password happens explicitly here, not via factory_boy's
        # deprecated implicit re-save after post-generation hooks.
        self.set_password(extracted or "password123")
        if create:
            self.save()


class SkillFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Skill

    name = factory.Sequence(lambda n: f"Skill {n}")
    tenant = factory.SubFactory(TenantFactory)

    @classmethod
    def _get_manager(cls, model_class):
        # Tenant is always supplied explicitly (or via SubFactory) to this factory, so
        # use the unscoped manager rather than forcing every caller to push a tenant
        # into context just to build fixtures (e.g. cross-tenant test setup).
        return model_class.objects_unscoped


class CrewSkillFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CrewSkill

    user = factory.SubFactory(UserFactory)
    skill = factory.SubFactory(SkillFactory, tenant=factory.SelfAttribute("..user.tenant"))
    tenant = factory.SelfAttribute("user.tenant")
    proficiency = 5

    @classmethod
    def _get_manager(cls, model_class):
        return model_class.objects_unscoped
