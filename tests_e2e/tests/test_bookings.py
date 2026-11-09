"""
End-to-end tests for the booking application cover the same business logic
as those found in `apps/bookings/tests.py` (e.g., `BookingModelTestCase`),
but they are verified via actual HTTP requests to a running server rather
than through direct, in-memory calls to `Booking.full_clean()`.

These are not mere copies of unit tests: model-level unit tests verify that
a `ValidationError` is raised when a model is instantiated directly within
Python, whereas these end-to-end tests ensure that the same rules are
enforced at the system boundary—following the very same contract that a
real-world client (such as a web or mobile application) would use. Both
levels of testing are maintained and complement one another; they do not
duplicate each other.
"""

from __future__ import annotations

from datetime import date

import pytest

from tests_e2e.fixtures.data import booking_payload, listing_payload

pytestmark = pytest.mark.django_db(transaction=True)


def _published_listing(landlord, **overrides) -> str:
    """Helper: create, set the price for, and publish a listing on behalf of
    a landlord; return the `listing_id`. The price must be provided separately
    from `current_price` in the payload — the `booking_service` retrieves the
    price from `PriceHistory` based on the check-in date, rather than from
    `Listing.current_price` (see `apps/bookings/services/booking_service.py`)."""
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


class TestBookingCreation:
    def test_tenant_can_create_booking_for_published_listing(self, tenant, landlord):
        listing_id = _published_listing(landlord)

        result = tenant.bookings.create(booking_payload(listing_id=listing_id))

        assert result.status == 201, result.data
        assert result.data["status"] == "pending"
        assert result.data["listing"] == listing_id

    def test_check_in_after_check_out_is_rejected(self, tenant, landlord):
        listing_id = _published_listing(landlord)

        result = tenant.bookings.create(
            booking_payload(
                listing_id=listing_id,
                check_in_date="2026-09-10",
                check_out_date="2026-09-05",
            )
        )

        assert result.status == 400, result.data

    def test_guests_count_exceeding_capacity_is_rejected(self, tenant, landlord):
        listing_id = _published_listing(landlord, max_guests=2)

        result = tenant.bookings.create(booking_payload(listing_id=listing_id, guests_count=10))

        assert result.status == 400, result.data

    def test_neither_listing_nor_room_is_rejected(self, tenant, landlord):
        listing_id = _published_listing(landlord)
        payload = booking_payload(listing_id=listing_id)
        payload.pop("listing_id")

        result = tenant.bookings.create(payload)

        assert result.status == 400, result.data

    def test_overlapping_dates_on_same_listing_is_rejected(self, tenant, landlord):
        """BookingNotAvailableError -> 409 Conflict (not 400): a more accurate
        HTTP status for a conflict involving a resource or dates that are already taken.
        """
        listing_id = _published_listing(landlord)
        payload = booking_payload(listing_id=listing_id)

        first = tenant.bookings.create(payload)
        assert first.status == 201, first.data

        second = tenant.bookings.create(payload)  # same dates, same listing
        assert second.status == 409, second.data

    def test_duration_exceeding_max_booking_days_is_rejected(self, tenant, landlord):
        """MAX_BOOKING_DURATION_DAYS = 365 (apps/bookings/constants)."""
        listing_id = _published_listing(landlord, rental_type="any")

        result = tenant.bookings.create(
            booking_payload(listing_id=listing_id, days_ahead=1, nights=400)
        )

        assert result.status == 400, result.data


class TestBookingLifecycle:
    def test_landlord_can_confirm_own_booking(self, tenant, landlord):
        listing_id = _published_listing(landlord)
        created = tenant.bookings.create(booking_payload(listing_id=listing_id))
        booking_id = created.data["id"]

        result = landlord.bookings.confirm(booking_id)

        assert result.status == 200, result.data
        assert result.data["status"] == "confirmed"

    def test_landlord_can_reject_own_booking(self, tenant, landlord):
        listing_id = _published_listing(landlord)
        created = tenant.bookings.create(booking_payload(listing_id=listing_id))
        booking_id = created.data["id"]

        result = landlord.bookings.reject(booking_id)

        assert result.status == 200, result.data
        assert result.data["status"] == "rejected"

    def test_stranger_landlord_cannot_confirm_someone_elses_booking(
        self, tenant, landlord, new_actor
    ):
        listing_id = _published_listing(landlord)
        created = tenant.bookings.create(booking_payload(listing_id=listing_id))
        booking_id = created.data["id"]

        stranger = new_actor()
        from tests_e2e.fixtures.data import register_payload

        stranger.auth.register(**register_payload(role="landlord", prefix="stranger"))

        result = stranger.bookings.confirm(booking_id)

        assert result.status in (403, 404), result.data


class TestBookingVisibility:
    def test_admin_sees_all_bookings_without_owning_any(self, tenant, landlord, admin_actor):
        """Regression test for a fixed bug: `list_for_user()` did not check
        for the admin role at all, which resulted in an empty list if the
        user had no bookings/listings of their own. See API_Endpoints_Reference,
        Booking section."""
        listing_id = _published_listing(landlord)
        created = tenant.bookings.create(booking_payload(listing_id=listing_id))
        assert created.status == 201, created.data

        result = admin_actor.bookings.list()

        assert result.status == 200, result.data
        booking_ids = [b["id"] for b in result.data]
        assert created.data["id"] in booking_ids

    def test_stranger_cannot_see_others_booking(self, tenant, landlord, new_actor):
        listing_id = _published_listing(landlord)
        created = tenant.bookings.create(booking_payload(listing_id=listing_id))
        booking_id = created.data["id"]

        stranger = new_actor()
        from tests_e2e.fixtures.data import register_payload

        stranger.auth.register(**register_payload(role="tenant", prefix="stranger"))

        result = stranger.bookings.get(booking_id)

        assert result.status in (403, 404), result.data


class TestBookingCancellation:
    def test_tenant_can_cancel_pending_booking_within_free_window(self, tenant, landlord):
        """TENANT_FREE_CANCEL_CUTOFF_HOURS = 24 — by default, a booking is created for 7 days
        in advance (booking_payload), which falls well within the free cancellation window;
        no reason is required (providing a reason is only applicable for the landlord).
        """
        listing_id = _published_listing(landlord)
        created = tenant.bookings.create(booking_payload(listing_id=listing_id))
        booking_id = created.data["id"]

        result = tenant.bookings.cancel(booking_id)

        assert result.status == 200, result.data
        assert result.data["status"] == "cancelled_by_tenant"

    def test_landlord_requires_cancellation_reason(self, tenant, landlord):
        listing_id = _published_listing(landlord)
        created = tenant.bookings.create(booking_payload(listing_id=listing_id))
        booking_id = created.data["id"]
        landlord.bookings.confirm(booking_id)

        result = landlord.bookings.cancel(booking_id)

        assert result.status == 400, result.data

    def test_landlord_can_cancel_with_reason(self, tenant, landlord, admin_actor):
        listing_id = _published_listing(landlord)
        created = tenant.bookings.create(booking_payload(listing_id=listing_id))
        booking_id = created.data["id"]
        landlord.bookings.confirm(booking_id)

        reasons = admin_actor.cancellation_reasons.list()
        reason_id = reasons.data[0]["id"]

        result = landlord.bookings.cancel(booking_id, cancellation_reason_id=reason_id)

        assert result.status == 200, result.data
        assert result.data["status"] == "cancelled_by_landlord"

    def test_stranger_cannot_cancel_someone_elses_booking(self, tenant, landlord, new_actor):
        listing_id = _published_listing(landlord)
        created = tenant.bookings.create(booking_payload(listing_id=listing_id))
        booking_id = created.data["id"]

        stranger = new_actor()
        from tests_e2e.fixtures.data import register_payload

        stranger.auth.register(**register_payload(role="tenant", prefix="stranger"))

        result = stranger.bookings.cancel(booking_id)

        assert result.status in (403, 404), result.data
