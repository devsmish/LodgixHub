"""
Role-based actor fixtures.

Tenants and landlords are created via the actual `/auth/register/`
endpoint—treated as a black box—without ever touching the ORM. This
also means that any regression in the registration process itself
will be caught by every test that uses these fixtures, rather than
just by a dedicated registration test.

You cannot create a user with the `moderator` or `admin` role this
way, as the `role` field in `RegisterSerializer` is restricted to
`GROUP_TENANT` and `GROUP_LANDLORD` (see `apps/security/dto/register.py`);
there is no public endpoint for elevating a user's role, nor should
there be. Therefore, the user is created via the Django ORM (using the
`db` fixture from `pytest-django`), and an access token is minted in
the same way that the actual `/auth/login/` endpoint would issue one
(using `RefreshToken` along with the mandatory `token_version`
claim—without which `CustomJWTAuthentication` returns a 401). The test
scenarios themselves then proceed to make standard HTTP requests.
"""
from __future__ import annotations

import pytest
from rest_framework_simplejwt.tokens import RefreshToken

from tests_e2e.actions.api.actor import APIActor
from tests_e2e.fixtures.data import register_payload


def _mint_access_token(user) -> str:
    refresh = RefreshToken.for_user(user)
    refresh["token_version"] = user.token_version
    return str(refresh.access_token)


@pytest.fixture
def tenant(new_actor) -> APIActor:
    actor = new_actor()
    payload = register_payload(role="tenant", prefix="tenant")
    result = actor.auth.register(**payload)
    assert result.ok, f"tenant registration failed: {result.status} {result.data}"
    return actor


@pytest.fixture
def landlord(new_actor) -> APIActor:
    actor = new_actor()
    payload = register_payload(role="landlord", prefix="landlord")
    result = actor.auth.register(**payload)
    assert result.ok, f"landlord registration failed: {result.status} {result.data}"
    return actor


@pytest.fixture
def moderator(new_actor, django_user_model, db) -> APIActor:
    from django.contrib.auth.models import Group

    from apps.security.constants import GROUP_MODERATOR

    group, _ = Group.objects.get_or_create(name=GROUP_MODERATOR)
    user = django_user_model.objects.create_user(
        email="moderator_e2e@e2e.test", password="TestPass123!"
    )
    user.groups.add(group)

    actor = new_actor()
    actor.use_token(_mint_access_token(user))
    return actor


@pytest.fixture
def admin_actor(new_actor, django_user_model, db) -> APIActor:
    from django.contrib.auth.models import Group

    from apps.security.constants import GROUP_ADMIN

    group, _ = Group.objects.get_or_create(name=GROUP_ADMIN)
    user = django_user_model.objects.create_user(
        email="admin_e2e@e2e.test", password="TestPass123!"
    )
    user.groups.add(group)

    actor = new_actor()
    actor.use_token(_mint_access_token(user))
    return actor
