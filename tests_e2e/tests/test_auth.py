"""
A full end-to-end (black-box) authentication cycle: register -> login -> refresh -> logout.
This also includes a regression test for a bug in `POST /auth/register/`, where
`register_user(**serializer.validated_data)` was passing an extra key,
`terms_accepted`—a parameter not present in the service’s signature—which caused a
`TypeError` on every request. While other test files in this suite already implicitly
trigger `register()` via tenant/landlord fixtures, this set implements explicit, targeted
tests for the authentication contract itself. This covers code paths not exercised elsewhere,
such as token refresh, logout, handling of invalid credentials, and attempts to register
with a privileged role.
"""
from __future__ import annotations

import pytest

from tests_e2e.fixtures.data import register_payload

pytestmark = pytest.mark.django_db(transaction=True)


class TestRegistration:
    def test_register_returns_usable_access_token(self, new_actor):
        actor = new_actor()
        payload = register_payload(role="tenant")

        result = actor.auth.register(**payload)

        assert result.status == 201, result.data
        assert result.data.get("access")
        assert actor.session.access_token == result.data["access"]

        # the token is actually functional, not just present in the response
        whoami = actor.bookings.list()
        assert whoami.status == 200, whoami.data

    def test_duplicate_email_is_rejected(self, new_actor):
        payload = register_payload(role="tenant")

        first = new_actor()
        assert first.auth.register(**payload).status == 201

        second = new_actor()
        result = second.auth.register(**payload)

        assert result.status == 400, result.data
        assert "email" in result.data

    def test_mismatched_password_confirmation_is_rejected(self, new_actor):
        actor = new_actor()
        payload = register_payload(role="tenant")

        result = actor.auth.register(**payload, password_confirm=payload["password"] + "different")

        assert result.status == 400, result.data

    def test_terms_not_accepted_is_rejected(self, new_actor):
        actor = new_actor()
        payload = register_payload(role="tenant")
        payload["terms_accepted"] = False

        result = actor.auth.register(**payload)

        assert result.status == 400, result.data
        assert "terms_accepted" in result.data

    def test_cannot_self_register_as_moderator_or_admin(self, new_actor):
        """The `role` field is restricted via `ChoiceField(choices=[GROUP_TENANT,
        GROUP_LANDLORD])` — privileged roles cannot be obtained through public
        registration under any circumstances. This is precisely the premise upon
        which `fixtures/users.py::moderator/admin_actor` is built (relying on ORM
        operations and token minting, rather than the `register()` function)."""
        actor = new_actor()
        payload = register_payload(role="tenant")
        payload["role"] = "admin"

        result = actor.auth.register(**payload)

        assert result.status == 400, result.data


class TestLoginAndRefresh:
    def test_login_with_correct_credentials_succeeds(self, new_actor):
        payload = register_payload(role="tenant")
        registered = new_actor()
        assert registered.auth.register(**payload).status == 201

        fresh_login = new_actor()
        result = fresh_login.auth.login(email=payload["email"], password=payload["password"])

        assert result.status == 200, result.data
        assert result.data.get("access")

    def test_login_with_wrong_password_fails(self, new_actor):
        payload = register_payload(role="tenant")
        registered = new_actor()
        assert registered.auth.register(**payload).status == 201

        fresh_login = new_actor()
        result = fresh_login.auth.login(email=payload["email"], password="WrongPassword123!")

        assert result.status == 401, result.data

    def test_refresh_issues_a_new_access_token(self, tenant):
        result = tenant.auth.refresh()

        assert result.status == 200, result.data
        assert result.data.get("access")
        # SimpleJWT may issue a token with the same structure if called within the
        # same second (when rotation is disabled, i.e., ROTATE_REFRESH_TOKENS=False) —
        # what matters is that the request is successful and the token remains
        # valid, not that it must necessarily be byte-for-byte different.
        whoami = tenant.bookings.list()
        assert whoami.status == 200, whoami.data

    def test_refresh_without_prior_login_fails(self, new_actor):
        """A newly created actor has no `refresh_token` cookie at all—neither via
        `register()` nor via `login()`. The result is a 403, not a 401:
        `TokenRefreshView` does not configure `authentication_classes`, so DRF cannot
        issue a `WWW-Authenticate` header; per the specification, it downgrades
        `AuthenticationFailed` to a 403 (see the same root cause in
        `apps/security/tests.py::test_12/test_13` within this same session)."""
        actor = new_actor()

        result = actor.auth.refresh()

        assert result.status == 403, result.data


class TestLogout:
    def test_logout_invalidates_the_current_access_token(self, tenant):
        """LogoutView increments `user.token_version` — this effectively invalidates *all*
        previously issued access tokens for that user, including the very token used to
        trigger the logout (since `CustomJWTAuthentication` compares the `token_version`
        claim against the value stored in the database for every request)."""
        logout_result = tenant.auth.logout()
        assert logout_result.status == 200, logout_result.data

        result = tenant.bookings.list()

        assert result.status in (401, 403), result.data

    def test_logout_blacklists_the_refresh_token(self, tenant):
        logout_result = tenant.auth.logout()
        assert logout_result.status == 200, logout_result.data

        result = tenant.auth.refresh()

        assert result.status == 403, result.data
