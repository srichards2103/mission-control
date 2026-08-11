from django.db import models


class Role(models.TextChoices):
    DIRECTOR = "director", "Director"
    MISSION_LEAD = "mission_lead", "Mission Lead"
    CREW_MEMBER = "crew_member", "Crew Member"
