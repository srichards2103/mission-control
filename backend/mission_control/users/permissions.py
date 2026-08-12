from enum import StrEnum

from rest_framework.exceptions import PermissionDenied

from mission_control.users.roles import Role


class Permission(StrEnum):
    MISSION_VIEW = "mission.view"
    MISSION_CREATE = "mission.create"
    MISSION_EDIT = "mission.edit"
    MISSION_PROGRESS = "mission.progress"
    MISSION_REVIEW = "mission.review"
    ASSIGNMENT_MANAGE = "assignment.manage"
    ASSIGNMENT_RESPOND = "assignment.respond"
    MATCH_RUN = "match.run"
    CREW_VIEW = "crew.view"
    USER_MANAGE = "user.manage"
    SKILL_VIEW = "skill.view"
    SKILL_MANAGE = "skill.manage"
    OWN_SKILLS_EDIT = "own_skills.edit"
    SETTINGS_VIEW = "settings.view"
    SETTINGS_MANAGE = "settings.manage"
    DASHBOARD_VIEW = "dashboard.view"


_CREW = frozenset(
    {Permission.SKILL_VIEW, Permission.OWN_SKILLS_EDIT, Permission.ASSIGNMENT_RESPOND}
)
_LEAD = frozenset(
    {
        Permission.MISSION_VIEW,
        Permission.MISSION_CREATE,
        Permission.MISSION_EDIT,
        Permission.MISSION_PROGRESS,
        Permission.ASSIGNMENT_MANAGE,
        Permission.MATCH_RUN,
        Permission.CREW_VIEW,
        Permission.SKILL_VIEW,
        Permission.DASHBOARD_VIEW,
    }
)
_DIRECTOR = frozenset(Permission) - {Permission.ASSIGNMENT_RESPOND, Permission.OWN_SKILLS_EDIT}

ROLE_PERMISSIONS: dict[str, frozenset[Permission]] = {
    Role.DIRECTOR: _DIRECTOR,
    Role.MISSION_LEAD: _LEAD,
    Role.CREW_MEMBER: _CREW,
}


def permissions_for_role(role: str) -> frozenset[Permission]:
    # `.get`, not `[]`: an unrecognised role (a hand-edited DB row, a role removed from
    # the catalogue while a session is live) must fail closed with a 403 from
    # `ensure_permission`, not a KeyError that escapes the error envelope as a 500.
    return ROLE_PERMISSIONS.get(role, frozenset())


def user_has_permission(user, perm: Permission) -> bool:
    return perm in permissions_for_role(user.role)


def ensure_permission(user, perm: Permission) -> None:
    if not user_has_permission(user, perm):
        raise PermissionDenied
