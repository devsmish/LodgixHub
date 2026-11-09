"""
Reviews — similar in spirit to Disputes: a review can only be left for a `completed` booking,
within a window of `REVIEW_WINDOW_DAYS=7` days after checkout. Since a booking cannot be set
to `completed` directly via the public API (this is handled by the `process_bookings` cron
job), the booking is—much like in `test_disputes.py`—properly created and confirmed via HTTP,
while the transition to the `completed` state (along with setting the dates to the past) is
emulated by directly modifying the ORM.
"""

from __future__ import annotations

from datetime import date, timedelta

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


def _completed_booking(tenant, landlord, *, days_since_checkout: int = 1) -> tuple[str, str]:
    """Returns (booking_id, listing_id)."""
    listing_id = _published_listing(landlord)
    created = tenant.bookings.create(
        booking_payload(listing_id=listing_id, days_ahead=5, nights=3)
    )
    assert created.status == 201, created.data
    booking_id = created.data["id"]

    confirmed = landlord.bookings.confirm(booking_id)
    assert confirmed.status == 200, confirmed.data

    from apps.bookings.choices import BookingStatus
    from apps.bookings.models import Booking

    check_out = date.today() - timedelta(days=days_since_checkout)
    check_in = check_out - timedelta(days=3)
    Booking.objects.filter(id=booking_id).update(
        check_in_date=check_in, check_out_date=check_out, status=BookingStatus.COMPLETED
    )
    return booking_id, listing_id


class TestReviewCreation:
    def test_tenant_can_review_completed_booking(self, tenant, landlord):
        booking_id, _ = _completed_booking(tenant, landlord)

        result = tenant.reviews.create(
            booking_id=booking_id, rating=5, comment="Great stay, very clean!"
        )

        assert result.status == 201, result.data
        assert result.data["status"] == "pending"

    def test_cannot_review_a_still_confirmed_booking(self, tenant, landlord):
        listing_id = _published_listing(landlord)
        created = tenant.bookings.create(booking_payload(listing_id=listing_id))
        booking_id = created.data["id"]
        landlord.bookings.confirm(booking_id)

        result = tenant.reviews.create(
            booking_id=booking_id, rating=5, comment="Too early to review."
        )

        assert result.status == 400, result.data

    def test_review_outside_the_seven_day_window_is_rejected(self, tenant, landlord):
        booking_id, _ = _completed_booking(tenant, landlord, days_since_checkout=10)

        result = tenant.reviews.create(
            booking_id=booking_id, rating=5, comment="Too late to review this stay."
        )

        assert result.status == 400, result.data

    def test_stranger_cannot_review_someone_elses_booking(self, tenant, landlord, new_actor):
        booking_id, _ = _completed_booking(tenant, landlord)

        stranger = new_actor()
        stranger.auth.register(**register_payload(role="tenant", prefix="stranger"))

        result = stranger.reviews.create(
            booking_id=booking_id, rating=1, comment="Not my booking at all."
        )

        assert result.status == 403, result.data

    def test_duplicate_review_for_same_booking_is_rejected(self, tenant, landlord):
        booking_id, _ = _completed_booking(tenant, landlord)
        first = tenant.reviews.create(
            booking_id=booking_id, rating=4, comment="First review, good stay."
        )
        assert first.status == 201, first.data

        second = tenant.reviews.create(
            booking_id=booking_id, rating=2, comment="Trying to review again."
        )

        assert second.status == 409, second.data


class TestReviewVisibilityAndModeration:
    def test_pending_review_is_not_visible_in_public_list(self, tenant, landlord, new_actor):
        booking_id, listing_id = _completed_booking(tenant, landlord)
        created = tenant.reviews.create(
            booking_id=booking_id, rating=5, comment="Awaiting moderation."
        )
        assert created.status == 201, created.data

        guest = new_actor()
        result = guest.reviews.list_for_listing(listing_id)

        assert result.status == 200, result.data
        review_ids = [r["id"] for r in result.data]
        assert created.data["id"] not in review_ids

    def test_published_review_is_visible_in_public_list(
        self, tenant, landlord, moderator, new_actor
    ):
        booking_id, listing_id = _completed_booking(tenant, landlord)
        created = tenant.reviews.create(
            booking_id=booking_id, rating=5, comment="Great, publish me."
        )
        review_id = created.data["id"]

        publish = moderator.reviews.update_status(review_id, status="published")
        assert publish.status == 200, publish.data

        guest = new_actor()
        result = guest.reviews.list_for_listing(listing_id)

        review_ids = [r["id"] for r in result.data]
        assert review_id in review_ids

    def test_regular_user_cannot_see_moderation_queue(self, tenant, landlord):
        booking_id, _ = _completed_booking(tenant, landlord)
        tenant.reviews.create(booking_id=booking_id, rating=5, comment="Some review text here.")

        result = tenant.reviews.list_moderation_queue()

        assert result.status == 403, result.data

    def test_moderator_sees_moderation_queue(self, tenant, landlord, moderator):
        booking_id, _ = _completed_booking(tenant, landlord)
        created = tenant.reviews.create(
            booking_id=booking_id, rating=5, comment="Needs moderation please."
        )

        result = moderator.reviews.list_moderation_queue()

        assert result.status == 200, result.data
        review_ids = [r["id"] for r in result.data]
        assert created.data["id"] in review_ids

    def test_non_moderator_cannot_update_review_status(self, tenant, landlord):
        booking_id, _ = _completed_booking(tenant, landlord)
        created = tenant.reviews.create(
            booking_id=booking_id, rating=5, comment="Trying to self-publish."
        )

        result = tenant.reviews.update_status(created.data["id"], status="published")

        assert result.status == 403, result.data


class TestReviewEditingAndResponse:
    def test_author_can_edit_review_within_window(self, tenant, landlord):
        booking_id, _ = _completed_booking(tenant, landlord)
        created = tenant.reviews.create(
            booking_id=booking_id, rating=3, comment="Initial, so-so review text."
        )
        review_id = created.data["id"]

        result = tenant.reviews.update(
            review_id, rating=5, comment="Actually it grew on me, updated review."
        )

        assert result.status == 200, result.data
        assert result.data["rating"] == 5

    def test_stranger_cannot_edit_someone_elses_review(self, tenant, landlord, new_actor):
        booking_id, _ = _completed_booking(tenant, landlord)
        created = tenant.reviews.create(
            booking_id=booking_id, rating=3, comment="Original review text here."
        )
        review_id = created.data["id"]

        stranger = new_actor()
        stranger.auth.register(**register_payload(role="tenant", prefix="stranger"))

        result = stranger.reviews.update(review_id, rating=1, comment="Hijacked review comment.")

        assert result.status == 403, result.data

    def test_landlord_can_respond_to_review_on_own_listing(self, tenant, landlord):
        booking_id, _ = _completed_booking(tenant, landlord)
        created = tenant.reviews.create(
            booking_id=booking_id, rating=5, comment="Wonderful place to stay!"
        )
        review_id = created.data["id"]

        result = landlord.reviews.respond(
            review_id, response_text="Thank you so much for staying with us!"
        )

        assert result.status == 200, result.data
        assert result.data["landlord_response"] == "Thank you so much for staying with us!"

    def test_stranger_landlord_cannot_respond_to_someone_elses_listing_review(
        self, tenant, landlord, new_actor
    ):
        booking_id, _ = _completed_booking(tenant, landlord)
        created = tenant.reviews.create(
            booking_id=booking_id, rating=5, comment="Nice place, would return."
        )
        review_id = created.data["id"]

        stranger_landlord = new_actor()
        stranger_landlord.auth.register(**register_payload(role="landlord", prefix="stranger"))

        result = stranger_landlord.reviews.respond(
            review_id, response_text="This is not even my listing."
        )

        assert result.status == 403, result.data
