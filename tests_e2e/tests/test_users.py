"""
The "Users" module is the one with the most extensive permission set: an admin can block,
unblock, or change the roles of other users' accounts. Furthermore, a "public" profile is
not truly public—it is only accessible if the viewer shares an active or completed
booking with the profile owner. Additionally, there is a guard in place to prevent the
deletion or blocking of any user who has active bookings.
"""

from __future__ import annotations

from datetime import date

import pytest

from tests_e2e.fixtures.data import booking_payload, listing_payload, register_payload

pytestmark = pytest.mark.django_db(transaction=True)


def _published_listing(landlord, **overrides) -> str:
    result = landlord.listings.create(listing_payload(**overrides))
    assert result.ok, f"listing creation failed: {result.status} {result.data}"
    listing_id = result.data["id"]

    price_result = landlord.listings.set_price(
        listing_id, price="100.00", valid_from=date.today().isoformat()
    )
    assert price_result.ok, f"set_price failed: {price_result.status} {price_result.data}"

    publish_result = landlord.listings.publish(listing_id)
    assert publish_result.ok, f"publish failed: {publish_result.status} {publish_result.data}"
    return listing_id


class TestOwnProfile:
    def test_authenticated_user_can_view_own_profile(self, tenant):
        result = tenant.users.me()

        assert result.status == 200, result.data
        assert "email" in result.data

    def test_authenticated_user_can_update_own_profile(self, tenant):
        result = tenant.users.update_me({"first_name": "Updated"})

        assert result.status == 200, result.data
        assert result.data["first_name"] == "Updated"

    def test_anonymous_cannot_access_me(self, new_actor):
        guest = new_actor()

        result = guest.users.me()

        assert result.status in (401, 403), result.data


class TestPublicProfileAccess:
    def test_stranger_cannot_view_public_profile_without_shared_booking(
        self, tenant, landlord, new_actor
    ):
        stranger = new_actor()
        stranger.auth.register(**register_payload(role="tenant", prefix="stranger"))

        landlord_id = landlord.session.user_id or landlord.users.me().data["id"]
        result = stranger.users.get_public_profile(landlord_id)

        assert result.status == 403, result.data

    def test_tenant_with_pending_booking_can_view_landlord_profile(self, tenant, landlord):
        """Regression involving a nested tuple.
        A bug was identified and fixed: `COMPLETED_OR_ACTIVE_STATUSES` in
        `apps/bookings/guards/user_guard.py` was defined as a nested tuple—
        `((PENDING, CONFIRMED), COMPLETED)`—rather than a flat one. In the Django ORM,
        using this value with `status__in` effectively matches only `COMPLETED`.
        Consequently, a user with an ongoing (i.e., `pending` or `confirmed`) booking
        was denied access to the owner's public profile, even though the docstring
        and the error message for `PublicProfileNotAccessibleError` explicitly
        promise access for "active or completed" bookings."""
        listing_id = _published_listing(landlord)
        created = tenant.bookings.create(booking_payload(listing_id=listing_id))
        assert created.status == 201, created.data

        landlord_id = landlord.users.me().data["id"]
        result = tenant.users.get_public_profile(landlord_id)

        assert result.status == 200, result.data


class TestAdminUserManagement:
    def test_regular_user_cannot_list_users(self, tenant):
        result = tenant.users.list_users()

        assert result.status == 403, result.data

    def test_moderator_can_list_users(self, moderator):
        result = moderator.users.list_users()

        assert result.status == 200, result.data

    def test_admin_can_block_user_with_valid_reason(self, tenant, admin_actor):
        tenant_id = tenant.users.me().data["id"]

        result = admin_actor.users.block(tenant_id, reason="SPAM")

        assert result.status == 200, result.data
        assert result.data["blocked_reason"] == "SPAM"

    def test_block_with_invalid_reason_is_rejected(self, tenant, admin_actor):
        tenant_id = tenant.users.me().data["id"]

        result = admin_actor.users.block(tenant_id, reason="NOT_A_REAL_REASON")

        assert result.status == 400, result.data

    def test_cannot_double_block_already_blocked_user(self, tenant, admin_actor):
        tenant_id = tenant.users.me().data["id"]
        first = admin_actor.users.block(tenant_id, reason="SPAM")
        assert first.status == 200, first.data

        second = admin_actor.users.block(tenant_id, reason="FRAUD")

        assert second.status == 409, second.data

    def test_non_admin_cannot_block_user(self, tenant, landlord, moderator):
        tenant_id = tenant.users.me().data["id"]

        result = moderator.users.block(tenant_id, reason="SPAM")

        assert result.status == 403, result.data

    def test_admin_can_unblock_user(self, tenant, admin_actor):
        tenant_id = tenant.users.me().data["id"]
        admin_actor.users.block(tenant_id, reason="SPAM")

        result = admin_actor.users.unblock(tenant_id)

        assert result.status == 200, result.data
        assert result.data["blocked_at"] is None

    def test_cannot_unblock_a_user_who_is_not_blocked(self, tenant, admin_actor):
        tenant_id = tenant.users.me().data["id"]

        result = admin_actor.users.unblock(tenant_id)

        assert result.status == 409, result.data

    def test_admin_can_update_user_groups(self, tenant, admin_actor):
        tenant_id = tenant.users.me().data["id"]

        result = admin_actor.users.update_groups(tenant_id, groups=["landlord"])

        assert result.status == 200, result.data
        assert "landlord" in result.data["groups"]


class TestActiveBookingGuards:
    def test_tenant_with_active_booking_cannot_self_delete(self, tenant, landlord):
        listing_id = _published_listing(landlord)
        created = tenant.bookings.create(booking_payload(listing_id=listing_id))
        assert created.status == 201, created.data

        result = tenant.users.delete_me()

        assert result.status == 409, result.data

    def test_landlord_with_active_booking_cannot_be_blocked(self, tenant, landlord, admin_actor):
        """Guard checks both parties — both the tenant and the landlord."""
        listing_id = _published_listing(landlord)
        created = tenant.bookings.create(booking_payload(listing_id=listing_id))
        assert created.status == 201, created.data

        landlord_id = landlord.users.me().data["id"]
        result = admin_actor.users.block(landlord_id, reason="SPAM")

        assert result.status == 409, result.data

    def test_admin_cannot_delete_user_with_active_bookings(self, tenant, landlord, admin_actor):
        listing_id = _published_listing(landlord)
        created = tenant.bookings.create(booking_payload(listing_id=listing_id))
        assert created.status == 201, created.data

        tenant_id = tenant.users.me().data["id"]
        result = admin_actor.users.delete_user(tenant_id)

        assert result.status == 409, result.data

    def test_tenant_without_active_bookings_can_self_delete(self, tenant):
        result = tenant.users.delete_me()

        assert result.status in (200, 204), result.data
