"""Seed two demo tenants with users, skills, crew and missions across all seven states.

Idempotent and atomic:
  * The whole command runs inside one `transaction.atomic()` block (Task 1.6's
    obligation) -- a mid-run failure leaves the database exactly as it was.
  * Users/skills/crew-skills use check-then-create (`get_or_create`-style) guards.
  * Per-tenant mission-building is gated on whether that tenant's own sentinel
    mission (the last one this command creates for it) already exists, read through
    the scoped `objects` manager with that tenant's id in context. A plain
    "any mission exists" guard -- the brief's sample
    (`Mission.objects_unscoped.filter(tenant=tenant).exists()`) -- is both unsafe to
    use here (a long-lived dev database can carry unrelated missions other work
    created under these same tenant slugs, which would make the guard skip seeding
    entirely) and, per the Global Constraints, `objects_unscoped` is for
    migrations/tests only and must never appear in application code, which a
    management command is. The sentinel check is robust to either problem and still
    genuinely idempotent: once this command's own missions exist, re-running it is a
    no-op.
  * Every `TenantModel` write (Skill, CrewSkill, Mission, MissionRequirement,
    Assignment) happens with `set_current_tenant_id` in effect, reset in a `finally`.

The dataset is built almost entirely through the real services
(`mission_create`, `mission_requirements_set`, `transition_mission`,
`assignments_propose`, `assignment_respond`) rather than by poking `.status` fields
directly, so every mission it produces is one the FSM and staffing guards actually
accept -- the same guards a reviewer will exercise by hand.

Build-order note: Ganymede Survey and Europa Ice Core (both left pending_approval)
are built and staffed *before* Titan Relay Deploy is approved. `assignments_propose`
refuses to staff someone who is hard-blocked *at propose time*, so staffing crew3
onto Ganymede only works while no approved/active mission yet holds them. Titan is
approved afterwards, which retroactively makes crew3 hard-blocked on Ganymede's still-
pending roster (a real conflict that arose after the fact -- exactly what the guard is
for) without ever tripping the propose-time check.
"""

import datetime as dt

from django.core.management.base import BaseCommand
from django.db import transaction

from mission_control.missions.models import Mission
from mission_control.missions.services.assignments import assignment_respond, assignments_propose
from mission_control.missions.services.missions import (
    mission_create,
    mission_requirements_set,
    transition_mission,
)
from mission_control.tenants.context import reset_current_tenant_id, set_current_tenant_id
from mission_control.tenants.models import Tenant
from mission_control.users.models import CrewSkill, Skill, User
from mission_control.users.roles import Role

DEMO_PASSWORD = "orbit-demo-2026"

SKILL_NAMES = [
    "Piloting",
    "Navigation",
    "EVA Ops",
    "Life Support",
    "Robotics",
    "Geology",
    "Comms",
    "Medicine",
]
ARCHIVED_SKILL_NAME = "Legacy Telemetry"

# "sentinel": the name of the last mission each tenant's build creates, used to
# gate whether that tenant's mission set needs building at all (see module docstring).
TENANTS = [
    {
        "name": "Helios Aerospace", "slug": "helios-aerospace", "crew_count": 15,
        "sentinel": "Vesta Sample Return",
    },
    {
        "name": "Meridian Orbital", "slug": "meridian-orbital", "crew_count": 8,
        "sentinel": "Rhea Ice Survey",
    },
]


def _d(offset_days: int) -> dt.date:
    return dt.date.today() + dt.timedelta(days=offset_days)


class Command(BaseCommand):
    help = "Seed two demo tenants with users, skills, crew and missions (idempotent)."

    @transaction.atomic
    def handle(self, *args, **options):
        for spec in TENANTS:
            tenant, _ = Tenant.objects.get_or_create(
                slug=spec["slug"], defaults={"name": spec["name"]}
            )
            token = set_current_tenant_id(tenant.id)
            try:
                director, lead, crew, skills = self._seed_users_and_skills(tenant, spec)
                if not Mission.objects.filter(name=spec["sentinel"]).exists():
                    if spec["slug"] == "helios-aerospace":
                        self._build_helios_missions(director, lead, crew, skills)
                    else:
                        self._build_meridian_missions(director, lead, crew, skills)
            finally:
                reset_current_tenant_id(token)
        self.stdout.write(self.style.SUCCESS("Seeded demo data."))

    # -- users, skills, crew skills -----------------------------------------------

    def _get_or_create_user(self, *, email, tenant, role, name):
        # User.objects is a plain, non-tenant-scoped manager (see project
        # constraints) -- email is globally unique, so this check needs no tenant
        # context and is safe to run before the tenant is set in context.
        user = User.objects.filter(email=email).first()
        if user is None:
            user = User.objects.create_user(
                email=email, password=DEMO_PASSWORD, tenant=tenant, role=role, name=name
            )
        return user

    def _seed_users_and_skills(self, tenant, spec):
        slug = spec["slug"]
        label = spec["name"].split()[0]

        director = self._get_or_create_user(
            email=f"director@{slug}.test", tenant=tenant, role=Role.DIRECTOR,
            name=f"{label} Director",
        )
        lead = self._get_or_create_user(
            email=f"lead@{slug}.test", tenant=tenant, role=Role.MISSION_LEAD,
            name=f"{label} Mission Lead",
        )
        crew = [
            self._get_or_create_user(
                email=f"crew{i + 1}@{slug}.test", tenant=tenant, role=Role.CREW_MEMBER,
                name=f"Crew {i + 1}",
            )
            for i in range(spec["crew_count"])
        ]

        skills = {}
        for name in SKILL_NAMES:
            skill, _ = Skill.objects.get_or_create(name=name)
            skills[name] = skill
        archived, created = Skill.objects.get_or_create(
            name=ARCHIVED_SKILL_NAME, defaults={"is_archived": True}
        )
        if not created and not archived.is_archived:
            archived.is_archived = True
            archived.save(update_fields=["is_archived"])

        # Deterministic, varied skill/proficiency spread: no ties, no randomness.
        # Crew member i gets skills[(i+j) % 8] at proficiency 3 + (i*2+j) % 8, for
        # j in range(2 + i % 3) -- 2 to 4 skills each.
        skill_order = [skills[name] for name in SKILL_NAMES]
        for i, user in enumerate(crew):
            skill_count = 2 + (i % 3)
            for j in range(skill_count):
                skill = skill_order[(i + j) % len(skill_order)]
                proficiency = 3 + (i * 2 + j) % 8
                CrewSkill.objects.get_or_create(
                    user=user, skill=skill, defaults={"proficiency": proficiency}
                )

        return director, lead, crew, skills

    # -- mission-building helpers ---------------------------------------------------

    def _mission(self, *, actor, name, start_offset, end_offset, min_crew, max_crew, requirements):
        mission = mission_create(
            actor=actor,
            name=name,
            description=f"Demo mission: {name}.",
            start_date=_d(start_offset),
            end_date=_d(end_offset),
            min_crew=min_crew,
            max_crew=max_crew,
        )
        if requirements:
            mission_requirements_set(
                actor=actor,
                mission=mission,
                items=[
                    {"skill_id": skill.id, "min_proficiency": prof, "required_count": count}
                    for skill, prof, count in requirements
                ],
            )
        return mission

    def _staff_and_accept(self, *, actor, mission, users):
        """Propose `users` and immediately have each of them accept."""
        created = assignments_propose(actor=actor, mission=mission, user_ids=[u.id for u in users])
        by_user = {a.user_id: a for a in created}
        for user in users:
            assignment_respond(actor=user, assignment=by_user[user.id], action="accept")

    # -- Helios Aerospace: the full-size tenant --------------------------------------

    def _build_helios_missions(self, director, lead, crew, skills):
        (
            crew1, crew2, crew3, crew4, crew5, crew6, crew7, crew8, crew9, crew10,
            crew11, crew12, crew13, crew14, crew15,
        ) = crew

        # 1. draft, requirements set, no assignments. EVA Ops >=7 demands 3 seats but
        # only crew3 and crew11 qualify org-wide -- the dashboard's skill-gap card has
        # something to report, and it's also the demo tour's auto-match target.
        self._mission(
            actor=lead, name="Callisto Flyby Prep", start_offset=40, end_offset=50,
            min_crew=2, max_crew=5,
            requirements=[(skills["EVA Ops"], 7, 3), (skills["Geology"], 5, 1)],
        )

        # 2. pending_approval, deliberately under-covered: Navigation 1/2, Piloting
        # 0/1 -- attempting to approve this from the UI is refused by the staffing
        # guard. crew3 is staffed here *before* Titan (below) exists/is approved, so
        # this propose call is never itself hard-blocked.
        ganymede = self._mission(
            actor=lead, name="Ganymede Survey", start_offset=14, end_offset=24,
            min_crew=3, max_crew=5,
            requirements=[(skills["Navigation"], 5, 2), (skills["Piloting"], 5, 1)],
        )
        self._staff_and_accept(actor=lead, mission=ganymede, users=[crew1, crew2, crew3])
        ganymede = transition_mission(actor=lead, mission=ganymede, action="submit")

        # 3. pending_approval, overlapping crew2 with Ganymede Survey while both are
        # still pending -- the soft-conflict showcase. crew1 gets an unresponded
        # ("proposed") assignment here too.
        europa = self._mission(
            actor=lead, name="Europa Ice Core", start_offset=16, end_offset=26,
            min_crew=1, max_crew=4,
            requirements=[(skills["Life Support"], 5, 1)],
        )
        self._staff_and_accept(actor=lead, mission=europa, users=[crew2])
        assignments_propose(actor=lead, mission=europa, user_ids=[crew1.id])
        europa = transition_mission(actor=lead, mission=europa, action="submit")

        # 4. approved, fully staffed. Approved last among these three: once approved,
        # crew3's acceptance here retroactively hard-blocks them on Ganymede's
        # (still-pending) roster -- the hard-block showcase, alongside crew2's soft
        # conflict, both visible on Ganymede's staffing panel.
        titan = self._mission(
            actor=lead, name="Titan Relay Deploy", start_offset=7, end_offset=20,
            min_crew=3, max_crew=4,
            requirements=[(skills["Piloting"], 5, 2), (skills["Navigation"], 5, 1)],
        )
        self._staff_and_accept(actor=lead, mission=titan, users=[crew6, crew8, crew10, crew3])
        titan = transition_mission(actor=lead, mission=titan, action="submit")
        titan = transition_mission(actor=director, mission=titan, action="approve")

        # 5. active, accepted crew, full transition history. Own crew, non-overlapping
        # with anything above.
        orbital = self._mission(
            actor=lead, name="Orbital Debris Sweep", start_offset=-3, end_offset=4,
            min_crew=1, max_crew=3,
            requirements=[(skills["Robotics"], 5, 1)],
        )
        self._staff_and_accept(actor=lead, mission=orbital, users=[crew4, crew5])
        orbital = transition_mission(actor=lead, mission=orbital, action="submit")
        orbital = transition_mission(actor=director, mission=orbital, action="approve")
        orbital = transition_mission(actor=lead, mission=orbital, action="activate")

        # 6. completed, full transition history.
        solar = self._mission(
            actor=lead, name="Solar Array Refit", start_offset=-30, end_offset=-20,
            min_crew=1, max_crew=3,
            requirements=[(skills["Geology"], 4, 1)],
        )
        self._staff_and_accept(actor=lead, mission=solar, users=[crew13, crew14])
        solar = transition_mission(actor=lead, mission=solar, action="submit")
        solar = transition_mission(actor=director, mission=solar, action="approve")
        solar = transition_mission(actor=lead, mission=solar, action="activate")
        solar = transition_mission(actor=lead, mission=solar, action="complete")

        # 7. rejected, with reason.
        asteroid = self._mission(
            actor=lead, name="Asteroid Prospecting", start_offset=25, end_offset=35,
            min_crew=1, max_crew=3,
            requirements=[(skills["Comms"], 5, 1)],
        )
        asteroid = transition_mission(actor=lead, mission=asteroid, action="submit")
        asteroid = transition_mission(
            actor=director, mission=asteroid, action="reject", reason="Budget window closed"
        )

        # 8. cancelled -- crew proposed/accepted first, then removed by the cancel.
        antenna = self._mission(
            actor=lead, name="Deep Space Antenna", start_offset=45, end_offset=55,
            min_crew=1, max_crew=3,
            requirements=[(skills["Comms"], 5, 1)],
        )
        created = assignments_propose(
            actor=lead, mission=antenna, user_ids=[crew7.id, crew9.id]
        )
        by_user = {a.user_id: a for a in created}
        assignment_respond(actor=crew7, assignment=by_user[crew7.id], action="accept")
        antenna = transition_mission(
            actor=lead, mission=antenna, action="cancel", reason="Mission scrubbed"
        )

        # 9. draft, hosting crew1's declined assignment. With crew1's accepted
        # assignment on Ganymede and unresponded one on Europa above, crew1's
        # my-assignments page has all three groups populated.
        vesta = self._mission(
            actor=lead, name="Vesta Sample Return", start_offset=60, end_offset=65,
            min_crew=1, max_crew=3, requirements=[],
        )
        created = assignments_propose(actor=lead, mission=vesta, user_ids=[crew1.id])
        assignment_respond(
            actor=crew1, assignment=created[0], action="decline", reason="Family commitments"
        )

    # -- Meridian Orbital: the smaller tenant ----------------------------------------

    def _build_meridian_missions(self, director, lead, crew, skills):
        crew1, crew2, crew3, crew4, crew5, crew6, crew7, crew8 = crew

        # draft, no assignments.
        self._mission(
            actor=lead, name="Ceres Outpost Survey", start_offset=35, end_offset=42,
            min_crew=1, max_crew=3,
            requirements=[(skills["Robotics"], 8, 1), (skills["EVA Ops"], 6, 1)],
        )

        # pending_approval, deliberately under-covered (Medicine 1/2) -- the approve
        # guard blocks this one too, in the smaller tenant.
        vesta = self._mission(
            actor=lead, name="Vesta Mining Assessment", start_offset=10, end_offset=18,
            min_crew=2, max_crew=4,
            requirements=[(skills["Medicine"], 8, 2)],
        )
        self._staff_and_accept(actor=lead, mission=vesta, users=[crew7, crew1])
        vesta = transition_mission(actor=lead, mission=vesta, action="submit")

        # approved, fully staffed.
        pallas = self._mission(
            actor=lead, name="Pallas Cargo Run", start_offset=5, end_offset=15,
            min_crew=2, max_crew=3,
            requirements=[(skills["Piloting"], 8, 1), (skills["Navigation"], 4, 1)],
        )
        self._staff_and_accept(actor=lead, mission=pallas, users=[crew8, crew2])
        pallas = transition_mission(actor=lead, mission=pallas, action="submit")
        pallas = transition_mission(actor=director, mission=pallas, action="approve")

        # active, full transition history.
        iapetus = self._mission(
            actor=lead, name="Iapetus Comms Relay", start_offset=-2, end_offset=5,
            min_crew=1, max_crew=2,
            requirements=[(skills["Comms"], 5, 1)],
        )
        self._staff_and_accept(actor=lead, mission=iapetus, users=[crew5])
        iapetus = transition_mission(actor=lead, mission=iapetus, action="submit")
        iapetus = transition_mission(actor=director, mission=iapetus, action="approve")
        iapetus = transition_mission(actor=lead, mission=iapetus, action="activate")

        # completed, full transition history.
        rhea = self._mission(
            actor=lead, name="Rhea Ice Survey", start_offset=-25, end_offset=-15,
            min_crew=1, max_crew=2,
            requirements=[(skills["Geology"], 4, 1)],
        )
        self._staff_and_accept(actor=lead, mission=rhea, users=[crew6])
        rhea = transition_mission(actor=lead, mission=rhea, action="submit")
        rhea = transition_mission(actor=director, mission=rhea, action="approve")
        rhea = transition_mission(actor=lead, mission=rhea, action="activate")
        rhea = transition_mission(actor=lead, mission=rhea, action="complete")
