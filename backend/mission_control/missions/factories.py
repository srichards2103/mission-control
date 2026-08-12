import datetime as dt

import factory

from mission_control.missions.models import Assignment, Mission, MissionRequirement
from mission_control.tenants.factories import TenantModelFactory
from mission_control.users.factories import SkillFactory, TenantFactory, UserFactory
from mission_control.users.roles import Role


class MissionFactory(TenantModelFactory):
    class Meta:
        model = Mission

    tenant = factory.SubFactory(TenantFactory)
    name = factory.Sequence(lambda n: f"Mission {n}")
    # Relative dates: tests that rely on "starts in the future" (activate guard) stay valid forever.
    start_date = factory.LazyFunction(lambda: dt.date.today() + dt.timedelta(days=10))
    end_date = factory.LazyFunction(lambda: dt.date.today() + dt.timedelta(days=20))
    min_crew = 1
    max_crew = 3
    created_by = factory.SubFactory(
        UserFactory, role=Role.MISSION_LEAD, tenant=factory.SelfAttribute("..tenant")
    )


class MissionRequirementFactory(TenantModelFactory):
    class Meta:
        model = MissionRequirement

    mission = factory.SubFactory(MissionFactory)
    tenant = factory.SelfAttribute("mission.tenant")
    skill = factory.SubFactory(SkillFactory, tenant=factory.SelfAttribute("..mission.tenant"))
    min_proficiency = 5
    required_count = 1


class AssignmentFactory(TenantModelFactory):
    class Meta:
        model = Assignment

    mission = factory.SubFactory(MissionFactory)
    tenant = factory.SelfAttribute("mission.tenant")
    user = factory.SubFactory(
        UserFactory, role=Role.CREW_MEMBER, tenant=factory.SelfAttribute("..mission.tenant")
    )
    created_by = factory.SelfAttribute("mission.created_by")
