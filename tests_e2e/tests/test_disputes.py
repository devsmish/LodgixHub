"""
Dispute/DisputeEvidence is the project node with the most complex role-based
permission structure. This file primarily tests visibility and role-based
boundaries, rather than just the "happy path."

A specific detail of this setup: a dispute can only be opened for a "confirmed"
or "completed" booking, and only within a specific timeframe—starting after
check-in and ending no later than `DISPUTE_OPEN_WINDOW_DAYS=3` days after
check-out (see `apps/bookings/validators/dispute_validators.py`). Since the
public API prevents the creation of bookings with a past check-in date (enforced
by a validation check during creation), we use a direct Django ORM
modification—specifically `queryset.update()`, which bypasses `full_clean()` and
`save()`—to set a booking to a "past check-in" state. This is done only *after*
the booking has been created and confirmed via the standard HTTP flow. The booking
process and its confirmation are treated as a "black box," and the passage of
"N days" is simulated directly, as it would otherwise be impossible to verify
without manipulating the system clock on a live server.
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


def _confirmed_past_booking(tenant, landlord, *, days_since_checkout: int = 1) -> str:
    """Creates and confirms a booking via an HTTP-based "black box" mechanism, then
    uses an ORM to shift the dates into the past—specifically, into the window during
    which a dispute can be opened (i.e., after check-in, and no more than
    `DISPUTE_OPEN_WINDOW_DAYS` days after check-out). Returns the `booking_id`."""
    listing_id = _published_listing(landlord)
    created = tenant.bookings.create(booking_payload(listing_id=listing_id, days_ahead=5, nights=3))
    assert created.status == 201, created.data
    booking_id = created.data["id"]

    confirmed = landlord.bookings.confirm(booking_id)
    assert confirmed.status == 200, confirmed.data

    from apps.bookings.models import Booking

    check_out = date.today() - timedelta(days=days_since_checkout)
    check_in = check_out - timedelta(days=3)
    Booking.objects.filter(id=booking_id).update(check_in_date=check_in, check_out_date=check_out)
    return booking_id


class TestDisputeOpening:
    def test_tenant_can_open_dispute_on_confirmed_past_booking(self, tenant, landlord):
        booking_id = _confirmed_past_booking(tenant, landlord)

        result = tenant.disputes.open(
            booking_id, reason_category="CLEANLINESS", reason="The unit was not cleaned.", claim_amount="20.00"
        )

        assert result.status == 201, result.data
        assert result.data["status"] == "open"

    def test_landlord_can_also_open_a_counter_dispute(self, tenant, landlord):
        """Both parties to a booking can each pursue their own separate dispute simultaneously —
        the uniqueness of an active dispute is determined by the pair (booking, opened_by),
        rather than by the booking alone."""
        booking_id = _confirmed_past_booking(tenant, landlord)
        tenant_dispute = tenant.disputes.open(
            booking_id, reason_category="OTHER", reason="Tenant's claim.", claim_amount="10.00"
        )
        assert tenant_dispute.status == 201, tenant_dispute.data

        landlord_dispute = landlord.disputes.open(
            booking_id, reason_category="DAMAGED_PROPERTY", reason="Landlord's claim.", claim_amount="50.00"
        )
        assert landlord_dispute.status == 201, landlord_dispute.data

    def test_stranger_cannot_open_dispute_on_someone_elses_booking(self, tenant, landlord, new_actor):
        booking_id = _confirmed_past_booking(tenant, landlord)

        stranger = new_actor()
        stranger.auth.register(**register_payload(role="tenant", prefix="stranger"))

        result = stranger.disputes.open(booking_id, reason_category="OTHER", reason="Not my booking.")

        assert result.status in (403, 404), result.data

    def test_cannot_open_dispute_on_pending_booking(self, tenant, landlord):
        """A dispute can only be opened for a confirmed/completed booking; a "pending"
        booking (one not yet confirmed by the owner) does not qualify."""
        listing_id = _published_listing(landlord)
        created = tenant.bookings.create(booking_payload(listing_id=listing_id))
        assert created.status == 201, created.data

        result = tenant.disputes.open(created.data["id"], reason_category="OTHER", reason="Too early.")

        assert result.status == 400, result.data

    def test_duplicate_active_dispute_from_same_opener_is_rejected(self, tenant, landlord):
        booking_id = _confirmed_past_booking(tenant, landlord)
        first = tenant.disputes.open(booking_id, reason_category="OTHER", reason="First claim.")
        assert first.status == 201, first.data

        second = tenant.disputes.open(booking_id, reason_category="OTHER", reason="Second claim, same opener.")

        assert second.status == 400, second.data

    def test_claim_amount_exceeding_total_price_is_rejected(self, tenant, landlord):
        booking_id = _confirmed_past_booking(tenant, landlord)

        result = tenant.disputes.open(
            booking_id, reason_category="OTHER", reason="Absurd claim.", claim_amount="999999.00"
        )

        assert result.status == 400, result.data


class TestDisputeVisibility:
    def test_regular_user_cannot_list_moderation_queue(self, tenant, landlord):
        """Regression test. GET /disputes/ — `get_permissions()` restricts the entire
        `list` action to the moderator/admin role (IsModerator | IsAdmin), with no
        partial access (i.e., "seeing only one's own items") for other users."""
        booking_id = _confirmed_past_booking(tenant, landlord)
        opened = tenant.disputes.open(booking_id, reason_category="OTHER", reason="x")
        assert opened.status == 201, opened.data

        result = tenant.disputes.list()

        assert result.status == 403, result.data

    def test_moderator_sees_dispute_in_moderation_queue(self, tenant, landlord, moderator):
        booking_id = _confirmed_past_booking(tenant, landlord)
        opened = tenant.disputes.open(booking_id, reason_category="OTHER", reason="x")
        assert opened.status == 201, opened.data

        result = moderator.disputes.list()

        assert result.status == 200, result.data
        dispute_ids = [d["id"] for d in result.data]
        assert opened.data["id"] in dispute_ids

    def test_both_booking_parties_and_moderator_can_see_dispute_detail(
        self, tenant, landlord, moderator
    ):
        booking_id = _confirmed_past_booking(tenant, landlord)
        opened = tenant.disputes.open(booking_id, reason_category="OTHER", reason="x")
        dispute_id = opened.data["id"]

        assert tenant.disputes.get(dispute_id).status == 200
        assert landlord.disputes.get(dispute_id).status == 200
        assert moderator.disputes.get(dispute_id).status == 200

    def test_stranger_cannot_see_dispute_detail(self, tenant, landlord, new_actor):
        booking_id = _confirmed_past_booking(tenant, landlord)
        opened = tenant.disputes.open(booking_id, reason_category="OTHER", reason="x")
        dispute_id = opened.data["id"]

        stranger = new_actor()
        stranger.auth.register(**register_payload(role="tenant", prefix="stranger"))

        result = stranger.disputes.get(dispute_id)

        assert result.status in (403, 404), result.data


class TestDisputeModeration:
    def test_moderator_can_review_and_resolve_full_lifecycle(self, tenant, landlord, moderator):
        booking_id = _confirmed_past_booking(tenant, landlord)
        opened = tenant.disputes.open(booking_id, reason_category="OTHER", reason="x", claim_amount="30.00")
        dispute_id = opened.data["id"]

        review_result = moderator.disputes.review(dispute_id)
        assert review_result.status == 200, review_result.data
        assert review_result.data["status"] == "under_review"

        resolve_result = moderator.disputes.resolve(
            dispute_id, status="resolved_refunded", resolution_favor="tenant", resolution_amount="30.00"
        )
        assert resolve_result.status == 200, resolve_result.data
        assert resolve_result.data["status"] == "resolved_refunded"

    def test_resolve_refunded_without_amount_is_rejected(self, tenant, landlord, moderator):
        booking_id = _confirmed_past_booking(tenant, landlord)
        opened = tenant.disputes.open(booking_id, reason_category="OTHER", reason="x")
        dispute_id = opened.data["id"]
        moderator.disputes.review(dispute_id)

        result = moderator.disputes.resolve(dispute_id, status="resolved_refunded", resolution_favor="tenant")

        assert result.status == 400, result.data

    def test_regular_participant_cannot_review_own_dispute(self, tenant, landlord):
        booking_id = _confirmed_past_booking(tenant, landlord)
        opened = tenant.disputes.open(booking_id, reason_category="OTHER", reason="x")
        dispute_id = opened.data["id"]

        result = tenant.disputes.review(dispute_id)

        assert result.status == 403, result.data


class TestDisputeEvidence:
    def test_participant_can_upload_and_both_parties_see_evidence(self, tenant, landlord):
        booking_id = _confirmed_past_booking(tenant, landlord)
        opened = tenant.disputes.open(booking_id, reason_category="OTHER", reason="x")
        dispute_id = opened.data["id"]

        upload = tenant.disputes.add_evidence(dispute_id, url="https://example.com/photo.jpg", description="proof")
        assert upload.status == 201, upload.data

        assert tenant.disputes.list_evidence(dispute_id).status == 200
        assert landlord.disputes.list_evidence(dispute_id).status == 200

    def test_stranger_cannot_see_or_upload_evidence(self, tenant, landlord, new_actor):
        booking_id = _confirmed_past_booking(tenant, landlord)
        opened = tenant.disputes.open(booking_id, reason_category="OTHER", reason="x")
        dispute_id = opened.data["id"]

        stranger = new_actor()
        stranger.auth.register(**register_payload(role="tenant", prefix="stranger"))

        assert stranger.disputes.list_evidence(dispute_id).status in (403, 404)
        upload = stranger.disputes.add_evidence(dispute_id, url="https://example.com/x.jpg")
        assert upload.status in (403, 404), upload.data

    def test_moderator_without_superuser_can_delete_someone_elses_evidence(
        self, tenant, landlord, moderator
    ):
        """Regression test for a fixed bug: DisputeEvidenceDetailView originally, it only
        checked for the `is_superuser` flag, rather than the `admin`/`moderator` group — as
        a result, a business moderator without the `is_superuser` flag could not delete
        evidence submitted by someone else."""
        booking_id = _confirmed_past_booking(tenant, landlord)
        opened = tenant.disputes.open(booking_id, reason_category="OTHER", reason="x")
        dispute_id = opened.data["id"]
        upload = tenant.disputes.add_evidence(dispute_id, url="https://example.com/photo.jpg")
        evidence_id = upload.data["id"]

        result = moderator.disputes.delete_evidence(dispute_id, evidence_id)

        assert result.status in (200, 204), result.data

    def test_author_can_delete_own_evidence(self, tenant, landlord):
        booking_id = _confirmed_past_booking(tenant, landlord)
        opened = tenant.disputes.open(booking_id, reason_category="OTHER", reason="x")
        dispute_id = opened.data["id"]
        upload = tenant.disputes.add_evidence(dispute_id, url="https://example.com/photo.jpg")
        evidence_id = upload.data["id"]

        result = tenant.disputes.delete_evidence(dispute_id, evidence_id)

        assert result.status in (200, 204), result.data
