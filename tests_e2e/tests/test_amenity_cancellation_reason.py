"""
Regression tests for a bug:
`Amenity.slug` and `CancellationReason.code` were both defined with
`choices=<closed enum>` and `unique=True`. Since all enum values were
pre-populated via a signal during deployment, it was physically impossible
for a `POST` request to create any new records: any provided value would
either fall outside the defined `choices` (resulting in a `400 invalid choice`
error) or conflict with an existing, pre-populated record (triggering a
`unique constraint` violation—though in practice, the process would fail
before reaching that point).

Fix: The `choices` constraint was removed from both fields, and regex
validation was added (`^[a-z][a-z0-9_]*$` for `slug`, `^[A-Z_]+$` for `code`).
The `unique=True` constraint was retained. The enum classes now serve
exclusively as a source of seed data for `post_migrate` signals.

This file verifies that:
a new value can be created;
attempting to duplicate an existing value fails due to a uniqueness constraint
(rather than an "invalid choice" error);
an invalid format is rejected by a regex;
access permissions (restricted to admins) remain intact following a field refactor.
"""
from __future__ import annotations

import random
import string
import uuid

import pytest

from tests_e2e.fixtures.data import register_payload

pytestmark = pytest.mark.django_db(transaction=True)


def _unique_slug() -> str:
    return f"e2e_amenity_{uuid.uuid4().hex[:8]}"


def _unique_code() -> str:
    # ^[A-Z_]+$ — uppercase letters and underscores only; no digits.
    suffix = "".join(random.choices(string.ascii_uppercase, k=8))
    return f"QA_REASON_{suffix}"


class TestAmenityChoicesUniqueBugRegression:
    def test_admin_can_create_amenity_with_slug_outside_seeded_enum(self, admin_actor):
        slug = _unique_slug()

        result = admin_actor.amenities.create(name="E2E Sauna", slug=slug, icon="sauna")

        assert result.status == 201, result.data
        assert result.data["slug"] == slug
        assert result.data["group"] == "basic"  # StandardAmenity.get_group_for_slug fallback

    def test_duplicate_slug_rejected_by_uniqueness_not_invalid_choice(self, admin_actor):
        slug = _unique_slug()
        first = admin_actor.amenities.create(name="E2E First", slug=slug)
        assert first.status == 201, first.data

        second = admin_actor.amenities.create(name="E2E Duplicate", slug=slug)

        assert second.status == 400, second.data
        assert "slug" in second.data
        assert "already exists" in str(second.data["slug"]).lower()

    def test_invalid_slug_format_is_rejected(self, admin_actor):
        result = admin_actor.amenities.create(name="Bad", slug="Not Valid! 123")

        assert result.status == 400, result.data
        assert "slug" in result.data

    def test_seeded_amenities_are_still_present_after_the_migration(self, admin_actor):
        """Regression the transition from `choices` to `free text + regex`:
        the existing seed values (for `StandardAmenity`) must remain accessible
        as standard records; they must not be lost during the field migration."""
        result = admin_actor.amenities.list()

        assert result.status == 200, result.data
        slugs = [a["slug"] for a in result.data]
        assert "wifi" in slugs

    def test_non_admin_cannot_create_amenity(self, landlord):
        result = landlord.amenities.create(name="E2E Sauna", slug=_unique_slug())

        assert result.status == 403, result.data

    def test_anonymous_can_list_amenities(self, new_actor):
        guest = new_actor()

        result = guest.amenities.list()

        assert result.status == 200, result.data


class TestCancellationReasonChoicesUniqueBugRegression:
    def test_admin_can_create_reason_with_code_outside_seeded_enum(self, admin_actor):
        code = _unique_code()

        result = admin_actor.cancellation_reasons.create(code=code, description="E2E custom reason")

        assert result.status == 201, result.data
        assert result.data["code"] == code

    def test_duplicate_code_rejected_by_uniqueness_not_invalid_choice(self, admin_actor):
        code = _unique_code()
        first = admin_actor.cancellation_reasons.create(code=code, description="First")
        assert first.status == 201, first.data

        second = admin_actor.cancellation_reasons.create(code=code, description="Duplicate")

        assert second.status == 400, second.data
        assert "code" in second.data
        assert "already exists" in str(second.data["code"]).lower()

    def test_lowercase_code_is_rejected_by_regex(self, admin_actor):
        """^[A-Z_]+$ — case is mandatory, unlike the original seed values for
        StandardCancellationReason.value (which were in lowercase; this is
        precisely why the source for population was switched to .name during the fix)."""
        result = admin_actor.cancellation_reasons.create(code="lowercase_code", description="x")

        assert result.status == 400, result.data
        assert "code" in result.data

    def test_seeded_reasons_use_uppercase_codes_after_the_fix(self, admin_actor):
        result = admin_actor.cancellation_reasons.list()

        assert result.status == 200, result.data
        codes = [r["code"] for r in result.data]
        assert "CHANGED_PLANS" in codes
        assert "changed_plans" not in codes  # старый (сломанный) формат сида

    def test_non_admin_cannot_create_cancellation_reason(self, tenant):
        result = tenant.cancellation_reasons.create(code=_unique_code(), description="x")

        assert result.status == 403, result.data

    def test_anonymous_cannot_list_cancellation_reasons(self, new_actor):
        """Unlike Amenity, the GET request here requires authorization (IsAuthenticated),
        rather than AllowAny."""
        guest = new_actor()

        result = guest.cancellation_reasons.list()

        assert result.status in (401, 403), result.data

    def test_authenticated_user_can_list_cancellation_reasons(self, tenant):
        result = tenant.cancellation_reasons.list()

        assert result.status == 200, result.data
