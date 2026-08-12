import pytest

from mission_control.users.factories import UserFactory

pytestmark = pytest.mark.django_db

CASES = [
    ("/api/v1/missions/", {"director": 200, "mission_lead": 200, "crew_member": 403}),
    ("/api/v1/crew/", {"director": 200, "mission_lead": 200, "crew_member": 403}),
    ("/api/v1/skills/", {"director": 200, "mission_lead": 200, "crew_member": 200}),
    ("/api/v1/settings/users/", {"director": 200, "mission_lead": 403, "crew_member": 403}),
    ("/api/v1/settings/organisation/", {"director": 200, "mission_lead": 403, "crew_member": 403}),
    ("/api/v1/dashboard/", {"director": 200, "mission_lead": 200, "crew_member": 403}),
    ("/api/v1/me/assignments/", {"director": 403, "mission_lead": 403, "crew_member": 200}),
    ("/api/v1/me/skills/", {"director": 403, "mission_lead": 403, "crew_member": 200}),
]


@pytest.mark.parametrize("url,expectations", CASES)
def test_rbac_matrix(auth_client_for, url, expectations):
    for role, expected in expectations.items():
        user = UserFactory(role=role)
        assert auth_client_for(user).get(url).status_code == expected, f"{role} GET {url}"
