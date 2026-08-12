from django.db import models
from django.db.models import F, Q

from mission_control.tenants.models import TenantModel
from mission_control.users.models import Skill, User


class MissionStatus(models.TextChoices):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# The two states nothing can leave (spec §8). A property of the lifecycle itself, so it
# lives with the status enum rather than inside whichever service first needed it.
TERMINAL_MISSION_STATUSES = frozenset({MissionStatus.COMPLETED, MissionStatus.CANCELLED})


class Mission(TenantModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=32, choices=MissionStatus.choices, default=MissionStatus.DRAFT
    )
    min_crew = models.PositiveSmallIntegerField()
    max_crew = models.PositiveSmallIntegerField()
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="created_missions")

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gte=F("start_date")),
                name="mission_dates_ordered",
                violation_error_message="End date must be on or after the start date.",
            ),
            models.CheckConstraint(
                condition=Q(min_crew__gte=1) & Q(max_crew__gte=F("min_crew")),
                name="mission_crew_bounds",
                violation_error_message=(
                    "Minimum crew must be at least 1 and at most maximum crew."
                ),
            ),
            models.UniqueConstraint(
                fields=["tenant", "id"],
                name="mission_tenant_id_uniq",
                violation_error_message="This mission does not belong to that organisation.",
            ),
        ]

    def __str__(self):
        return self.name


class MissionTransition(TenantModel):
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name="transitions")
    from_status = models.CharField(max_length=32, choices=MissionStatus.choices)
    to_status = models.CharField(max_length=32, choices=MissionStatus.choices)
    actor = models.ForeignKey(User, on_delete=models.PROTECT, related_name="+")
    reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]


class MissionRequirement(TenantModel):
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name="requirements")
    skill = models.ForeignKey(Skill, on_delete=models.PROTECT, related_name="+")
    min_proficiency = models.PositiveSmallIntegerField()
    required_count = models.PositiveSmallIntegerField(default=1)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(min_proficiency__gte=1) & Q(min_proficiency__lte=10),
                name="requirement_proficiency_1_10",
                violation_error_message="Minimum proficiency must be between 1 and 10.",
            ),
            models.CheckConstraint(
                condition=Q(required_count__gte=1),
                name="requirement_count_gte_1",
                violation_error_message="A requirement must ask for at least one crew member.",
            ),
            models.UniqueConstraint(
                fields=["mission", "skill", "min_proficiency"],
                name="requirement_mission_skill_prof_uniq",
                violation_error_message=(
                    "This skill is already required at that proficiency."
                ),
            ),
        ]


class AssignmentStatus(models.TextChoices):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    REMOVED = "removed"


# The one definition of "this assignment still holds a seat". Declared as an ordered
# tuple with the frozenset derived from it, because the two callers want different
# things: every membership test wants the set, while `assignment_live_uniq` below needs
# a stable *ordered* value -- a frozenset has no order, and `sorted(...)` would reorder
# the predicate already recorded in migration 0003, rebuilding the partial index for no
# semantic gain.
LIVE_ASSIGNMENT_STATUS_ORDER = (AssignmentStatus.PROPOSED, AssignmentStatus.ACCEPTED)
LIVE_ASSIGNMENT_STATUSES = frozenset(LIVE_ASSIGNMENT_STATUS_ORDER)


class Assignment(TenantModel):
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name="assignments")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="assignments")
    status = models.CharField(
        max_length=16, choices=AssignmentStatus.choices, default=AssignmentStatus.PROPOSED
    )
    decline_reason = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="+")
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["mission", "user"],
                # Read from the constant rather than restating it: the literal
                # ["proposed", "accepted"] sat seventeen lines below its own definition
                # and was free to drift from it.
                condition=Q(status__in=list(LIVE_ASSIGNMENT_STATUS_ORDER)),
                name="assignment_live_uniq",
                violation_error_message=(
                    "This crew member is already assigned to this mission."
                ),
            ),
        ]
