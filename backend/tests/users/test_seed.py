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
    assert User.objects.count() == 6
