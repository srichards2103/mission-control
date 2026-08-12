import pytest
from django.core.management import call_command

from mission_control.tenants.models import Tenant
from mission_control.users.models import User

pytestmark = pytest.mark.django_db


def test_seed_demo_idempotent():
    call_command("seed_demo")
    call_command("seed_demo")
    assert Tenant.objects.count() == 2
    assert User.objects.filter(email="director@helios-aerospace.test").exists()
    from mission_control.missions.models import Mission, MissionStatus

    helios = Tenant.objects.get(slug="helios-aerospace")
    statuses = set(Mission.objects_unscoped.filter(tenant=helios).values_list("status", flat=True))
    assert statuses == set(MissionStatus.values)
    assert User.objects.filter(tenant=helios).count() >= 17  # director + lead + 15 crew
