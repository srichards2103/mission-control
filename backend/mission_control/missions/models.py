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
                condition=Q(end_date__gte=F("start_date")), name="mission_dates_ordered"
            ),
            models.CheckConstraint(
                condition=Q(min_crew__gte=1) & Q(max_crew__gte=F("min_crew")),
                name="mission_crew_bounds",
            ),
            models.UniqueConstraint(fields=["tenant", "id"], name="mission_tenant_id_uniq"),
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
            ),
            models.CheckConstraint(
                condition=Q(required_count__gte=1), name="requirement_count_gte_1"
            ),
            models.UniqueConstraint(
                fields=["mission", "skill", "min_proficiency"],
                name="requirement_mission_skill_prof_uniq",
            ),
        ]
