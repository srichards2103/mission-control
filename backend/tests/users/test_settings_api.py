import pytest

from mission_control.users.factories import UserFactory
from mission_control.users.models import User
from mission_control.users.roles import Role

pytestmark = pytest.mark.django_db


def test_director_creates_user(auth_client_for):
    director = UserFactory(role=Role.DIRECTOR)
    resp = auth_client_for(director).post("/api/v1/settings/users/", {
        "email": "new@example.com", "name": "New Crew", "role": "crew_member",
        "password": "s3cret-pw",
    })
    assert resp.status_code == 201
    created = User.objects.get(email="new@example.com")
    assert created.tenant_id == director.tenant_id
    assert created.check_password("s3cret-pw")
    assert "password" not in resp.data


def test_lead_cannot_manage_users(auth_client_for):
    lead = UserFactory(role=Role.MISSION_LEAD)
    assert auth_client_for(lead).get("/api/v1/settings/users/").status_code == 403


def test_crew_cannot_manage_users(auth_client_for):
    crew = UserFactory(role=Role.CREW_MEMBER)
    assert auth_client_for(crew).post("/api/v1/settings/users/", {
        "email": "x@example.com", "name": "X", "role": "crew_member", "password": "s3cret-pw",
    }).status_code == 403


def test_deactivate_and_role_change(auth_client_for):
    director = UserFactory(role=Role.DIRECTOR)
    crew = UserFactory(role=Role.CREW_MEMBER, tenant=director.tenant)
    resp = auth_client_for(director).patch(f"/api/v1/settings/users/{crew.id}/",
                                           {"role": "mission_lead", "is_active": False})
    assert resp.status_code == 200
    crew.refresh_from_db()
    assert crew.role == Role.MISSION_LEAD and crew.is_active is False


def test_cannot_change_own_account(auth_client_for):
    director = UserFactory(role=Role.DIRECTOR)
    resp = auth_client_for(director).patch(
        f"/api/v1/settings/users/{director.id}/", {"is_active": False}
    )
    assert resp.status_code == 400


def test_organisation_rename(auth_client_for):
    director = UserFactory(role=Role.DIRECTOR)
    resp = auth_client_for(director).patch(
        "/api/v1/settings/organisation/", {"name": "Helios Renamed"}
    )
    assert resp.status_code == 200
    director.tenant.refresh_from_db()
    assert director.tenant.name == "Helios Renamed"


# --- Cross-tenant isolation: User is the one model whose default manager is NOT
# tenant-scoped, so these paths must be proven explicitly rather than trusted. ---


def test_user_list_is_tenant_scoped(auth_client_for):
    director = UserFactory(role=Role.DIRECTOR)
    UserFactory(role=Role.CREW_MEMBER, tenant=director.tenant, name="Own Crew")
    UserFactory(role=Role.CREW_MEMBER, name="Other Tenant Crew")  # different tenant
    resp = auth_client_for(director).get("/api/v1/settings/users/")
    assert resp.status_code == 200
    names = {row["name"] for row in resp.data["results"]}
    assert names == {director.name, "Own Crew"}


def test_cross_tenant_user_patch_is_404_not_403(auth_client_for):
    director = UserFactory(role=Role.DIRECTOR)
    other = UserFactory(role=Role.CREW_MEMBER)  # different tenant
    resp = auth_client_for(director).patch(
        f"/api/v1/settings/users/{other.id}/", {"is_active": False}
    )
    assert resp.status_code == 404
    other.refresh_from_db()
    assert other.is_active is True


def test_duplicate_email_across_tenants_is_400_not_500(auth_client_for):
    director = UserFactory(role=Role.DIRECTOR)
    UserFactory(email="taken@example.com")  # a different tenant entirely
    resp = auth_client_for(director).post("/api/v1/settings/users/", {
        "email": "taken@example.com", "name": "Dup", "role": "crew_member", "password": "s3cret-pw",
    })
    assert resp.status_code == 400
    assert resp.data["message"] == "Validation error"
    assert "email" in resp.data["extra"]["fields"]


def test_duplicate_email_case_insensitive(auth_client_for):
    director = UserFactory(role=Role.DIRECTOR)
    UserFactory(email="taken@example.com")
    resp = auth_client_for(director).post("/api/v1/settings/users/", {
        "email": "TAKEN@example.com", "name": "Dup", "role": "crew_member", "password": "s3cret-pw",
    })
    assert resp.status_code == 400
    assert resp.data["message"] == "Validation error"


def test_create_password_too_short(auth_client_for):
    director = UserFactory(role=Role.DIRECTOR)
    resp = auth_client_for(director).post("/api/v1/settings/users/", {
        "email": "short@example.com", "name": "Short", "role": "crew_member", "password": "short",
    })
    assert resp.status_code == 400


def test_organisation_get_scoped_to_own_tenant(auth_client_for):
    director = UserFactory(role=Role.DIRECTOR)
    resp = auth_client_for(director).get("/api/v1/settings/organisation/")
    assert resp.status_code == 200
    assert resp.data == {
        "id": director.tenant_id,
        "name": director.tenant.name,
        "slug": director.tenant.slug,
    }


def test_lead_cannot_view_organisation_settings(auth_client_for):
    lead = UserFactory(role=Role.MISSION_LEAD)
    assert auth_client_for(lead).get("/api/v1/settings/organisation/").status_code == 403


def test_lead_cannot_rename_organisation(auth_client_for):
    lead = UserFactory(role=Role.MISSION_LEAD)
    resp = auth_client_for(lead).patch("/api/v1/settings/organisation/", {"name": "Nope"})
    assert resp.status_code == 403
