from django.core.management.base import BaseCommand

from mission_control.tenants.models import Tenant
from mission_control.users.models import User
from mission_control.users.roles import Role

DEMO_PASSWORD = "orbit-demo-2026"
TENANTS = [("Helios Aerospace", "helios-aerospace"), ("Meridian Orbital", "meridian-orbital")]
ROLES = [("director", Role.DIRECTOR), ("lead", Role.MISSION_LEAD), ("crew1", Role.CREW_MEMBER)]


class Command(BaseCommand):
    help = "Seed demo tenants and users (idempotent)."

    def handle(self, *args, **options):
        for name, slug in TENANTS:
            tenant, _ = Tenant.objects.get_or_create(slug=slug, defaults={"name": name})
            for prefix, role in ROLES:
                email = f"{prefix}@{slug}.test"
                if not User.objects.filter(email=email).exists():
                    User.objects.create_user(
                        email=email, password=DEMO_PASSWORD, tenant=tenant,
                        role=role, name=f"{prefix.title()} {name.split()[0]}",
                    )
        self.stdout.write(self.style.SUCCESS("Seeded demo data."))
