"""Lost check-then-insert races stay inside the error envelope.

`skill_create` and `user_create` both ask "does this already exist?" with a non-locking
SELECT and then INSERT. Two concurrent requests can both pass the check before either
commits; the loser hits a DB unique constraint and raises `IntegrityError`, which
`common.exception_handler` does not recognise -- so before this fix the client got an
unenveloped 500 for what is, from their point of view, an ordinary duplicate.

The race is simulated deterministically (rather than by timing) by making the INSERT
raise exactly the `IntegrityError` Postgres would, standing in for "a concurrent request
committed between our check and our insert" -- the same technique as
`test_propose_concurrent_duplicate_returns_400_not_500`, which pins the third instance
of this pattern.
"""

from unittest.mock import patch

import pytest
from django.db import IntegrityError

from mission_control.users.factories import UserFactory
from mission_control.users.models import Skill, User
from mission_control.users.roles import Role

pytestmark = pytest.mark.django_db


def _raise_integrity_error(constraint):
    def _save(self, *args, **kwargs):
        raise IntegrityError(f'duplicate key value violates unique constraint "{constraint}"')

    return _save


def test_skill_create_concurrent_duplicate_is_400_not_500(auth_client_for):
    director = UserFactory(role=Role.DIRECTOR)
    client = auth_client_for(director)

    with patch.object(Skill, "save", _raise_integrity_error("skill_name_per_tenant_uniq")):
        resp = client.post("/api/v1/skills/", {"name": "EVA Ops"})

    assert resp.status_code == 400
    assert resp.data == {
        "message": "Validation error",
        "extra": {"fields": {"__all__": ["A skill with this name already exists."]}},
    }
    assert Skill.objects_unscoped.filter(name="EVA Ops").count() == 0
    # The savepoint left the connection usable: a normal retry still works.
    assert client.post("/api/v1/skills/", {"name": "EVA Ops"}).status_code == 201


def test_user_create_concurrent_duplicate_is_400_not_500(auth_client_for):
    director = UserFactory(role=Role.DIRECTOR)
    client = auth_client_for(director)
    body = {"email": "racer@example.com", "name": "Racer", "role": Role.CREW_MEMBER,
            "password": "s3cret-pw"}

    with patch.object(User, "save", _raise_integrity_error("users_user_email_key")):
        resp = client.post("/api/v1/settings/users/", body)

    assert resp.status_code == 400
    # Indistinguishable from the sequential duplicate, which is the point.
    assert resp.data == {
        "message": "Validation error",
        "extra": {"fields": {"email": ["A user with this email already exists."]}},
    }
    assert User.objects.filter(email="racer@example.com").count() == 0
    assert client.post("/api/v1/settings/users/", body).status_code == 201
