from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.choices import (
    BookingStatus,
    DisputeReason,
    DisputeResolutionFavor,
    DisputeStatus,
    StandardCancellationReason,
)
from apps.bookings.guards.user_guard import (
    COMPLETED_OR_ACTIVE_STATUSES,
    user_has_completed_booking_with_listing_owner,
)
from apps.bookings.models import Booking, CancellationReason
from apps.bookings.services import (
    add_evidence,
    calculate_auto_cancel_deadline,
    open_dispute,
    resolve_dispute,
    start_review,
)
from apps.listings.choices import ListingStatus, ListingType, RentalType
from apps.listings.models import Address, Listing
from apps.pricing.models import PriceHistory

User = get_user_model()


def make_address(**overrides):
    defaults = {
        "region": "Saarland",
        "city": "Saarlouis",
        "street": "Kaiser-Wilhelm-Straße",
        "house_number": "12",
        "postal_code": "66740",
    }
    defaults.update(overrides)
    return Address.objects.create(**defaults)


def age_booking_into_dispute_window(booking, *, days_since_checkout=1):
    today = timezone.now().date()
    check_in = today - timedelta(days=5 + days_since_checkout)
    check_out = today - timedelta(days=days_since_checkout)
    Booking.objects.filter(pk=booking.pk).update(
        status=BookingStatus.CONFIRMED,
        check_in_date=check_in,
        check_out_date=check_out,
    )
    booking.refresh_from_db()
    return booking


class CancellationReasonModelTestCase(TestCase):

    def test_str_returns_description(self):
        reason = CancellationReason.objects.get(
            code=StandardCancellationReason.CHANGED_PLANS.name
        )
        self.assertEqual(str(reason), reason.description)

    def test_code_uniqueness(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CancellationReason.objects.create(
                    code=StandardCancellationReason.CHANGED_PLANS.name, description="B"
                )


class BookingModelTestCase(TestCase):

    def setUp(self):
        self.tenant = User.objects.create_user(
            email="tenant@example.com", password="securepassword123"
        )
        self.landlord = User.objects.create_user(
            email="landlord@example.com", password="securepassword123"
        )
        self.listing = Listing.objects.create(
            owner=self.landlord,
            title="Test Listing",
            type=ListingType.APARTMENT,
            address=make_address(),
            max_guests=4,
            current_price=Decimal("1000.00"),
        )
        today = timezone.now().date()
        self.valid_data = {
            "tenant": self.tenant,
            "listing": self.listing,
            "check_in_date": today + timedelta(days=1),
            "check_out_date": today + timedelta(days=3),
            "guests_count": 2,
            "total_price": Decimal("2000.00"),
        }

    def test_create_valid_booking(self):
        booking = Booking.objects.create(**self.valid_data)
        self.assertIsNotNone(booking.id)
        self.assertEqual(booking.status, BookingStatus.PENDING)
        self.assertIsNone(booking.confirmed_at)
        self.assertIsNone(booking.cancelled_at)
        self.assertFalse(booking.deposit_refunded)

    def test_check_in_after_check_out_raises(self):
        self.valid_data["check_in_date"], self.valid_data["check_out_date"] = (
            self.valid_data["check_out_date"],
            self.valid_data["check_in_date"],
        )
        with self.assertRaises(ValidationError):
            Booking(**self.valid_data).full_clean()

    def test_check_in_in_the_past_raises(self):
        self.valid_data["check_in_date"] = timezone.now().date() - timedelta(days=1)
        with self.assertRaises(ValidationError):
            Booking(**self.valid_data).full_clean()

    def test_guests_count_zero_raises(self):
        self.valid_data["guests_count"] = 0
        with self.assertRaises(ValidationError):
            Booking(**self.valid_data).full_clean()

    def test_guests_count_exceeds_capacity_raises(self):
        self.valid_data["guests_count"] = 999
        with self.assertRaises(ValidationError):
            Booking(**self.valid_data).full_clean()

    def test_xor_listing_or_room_constraint(self):
        self.valid_data.pop("listing")
        with self.assertRaises(ValidationError):
            Booking(**self.valid_data).full_clean()

    def test_overlapping_dates_on_same_listing_raises(self):
        Booking.objects.create(**self.valid_data)

        overlapping = dict(self.valid_data)
        overlapping["tenant"] = self.tenant
        with self.assertRaises(ValidationError):
            Booking(**overlapping).full_clean()

    def test_cancelled_by_landlord_frees_up_dates(self):
        first = Booking.objects.create(**self.valid_data)
        first.status = BookingStatus.CANCELLED_BY_LANDLORD
        first.cancelled_at = timezone.now()
        first.save()

        second = dict(self.valid_data)
        second["tenant"] = self.tenant
        Booking(**second).full_clean()

    def test_update_existing_booking_without_dispute_does_not_crash(self):
        booking = Booking.objects.create(**self.valid_data)
        booking.guests_count = 3
        booking.full_clean()
        booking.save()
        self.assertEqual(booking.guests_count, 3)

    def test_modify_booking_with_open_dispute_raises(self):
        booking = Booking.objects.create(**self.valid_data)
        booking = age_booking_into_dispute_window(booking)
        open_dispute(
            booking=booking,
            opened_by=self.tenant,
            reason_category=DisputeReason.CLEANLINESS,
            reason="Room was dirty on arrival.",
        )

        booking.guests_count = 3
        with self.assertRaises(ValidationError):
            booking.full_clean()


class DisputeModelTestCase(TestCase):

    def setUp(self):
        self.tenant = User.objects.create_user(
            email="tenant2@example.com", password="securepassword123"
        )
        self.landlord = User.objects.create_user(
            email="landlord2@example.com", password="securepassword123"
        )
        self.stranger = User.objects.create_user(
            email="stranger@example.com", password="securepassword123"
        )
        self.listing = Listing.objects.create(
            owner=self.landlord,
            title="Dispute Test Listing",
            type=ListingType.APARTMENT,
            address=make_address(city="Berlin", street="Alexanderplatz", house_number="1"),
            max_guests=4,
            current_price=Decimal("1000.00"),
        )
        today = timezone.now().date()
        raw_booking = Booking.objects.create(
            tenant=self.tenant,
            listing=self.listing,
            check_in_date=today + timedelta(days=1),
            check_out_date=today + timedelta(days=3),
            guests_count=2,
            total_price=Decimal("2000.00"),
        )

        self.booking = age_booking_into_dispute_window(raw_booking)
        self.future_pending_booking = Booking.objects.create(
            tenant=self.tenant,
            listing=self.listing,
            check_in_date=today + timedelta(days=5),
            check_out_date=today + timedelta(days=7),
            guests_count=2,
            total_price=Decimal("2000.00"),
        )

    def test_open_dispute_by_tenant_success(self):
        dispute = open_dispute(
            booking=self.booking,
            opened_by=self.tenant,
            reason_category=DisputeReason.CLEANLINESS,
            reason="Not clean.",
        )
        self.assertEqual(dispute.status, DisputeStatus.OPEN)

    def test_open_dispute_by_landlord_success(self):
        dispute = open_dispute(
            booking=self.booking,
            opened_by=self.landlord,
            reason_category=DisputeReason.DAMAGED_PROPERTY,
            reason="Guest damaged the sofa.",
        )
        self.assertEqual(dispute.opened_by, self.landlord)

    def test_open_dispute_by_stranger_raises(self):

        with self.assertRaises(ValidationError):
            open_dispute(
                booking=self.booking,
                opened_by=self.stranger,
                reason_category=DisputeReason.OTHER,
                reason="Not my business, but still.",
            )

    def test_open_dispute_before_check_in_raises(self):

        with self.assertRaises(ValidationError):
            open_dispute(
                booking=self.future_pending_booking,
                opened_by=self.tenant,
                reason_category=DisputeReason.OTHER,
                reason="Too early.",
            )

    def test_open_dispute_on_pending_booking_raises(self):

        self.assertEqual(self.future_pending_booking.status, BookingStatus.PENDING)
        with self.assertRaises(ValidationError):
            open_dispute(
                booking=self.future_pending_booking,
                opened_by=self.tenant,
                reason_category=DisputeReason.OTHER,
                reason="Still pending.",
            )

    def test_open_dispute_after_window_raises(self):

        old_booking = age_booking_into_dispute_window(
            Booking.objects.create(
                tenant=self.tenant,
                listing=self.listing,
                check_in_date=timezone.now().date() + timedelta(days=1),
                check_out_date=timezone.now().date() + timedelta(days=3),
                guests_count=2,
                total_price=Decimal("2000.00"),
            ),
            days_since_checkout=10,
        )
        with self.assertRaises(ValidationError):
            open_dispute(
                booking=old_booking,
                opened_by=self.tenant,
                reason_category=DisputeReason.OTHER,
                reason="Too late.",
            )

    def test_second_active_dispute_same_author_raises(self):
        open_dispute(
            booking=self.booking,
            opened_by=self.tenant,
            reason_category=DisputeReason.CLEANLINESS,
            reason="First complaint.",
        )
        with self.assertRaises(ValidationError):
            open_dispute(
                booking=self.booking,
                opened_by=self.tenant,
                reason_category=DisputeReason.NOISE_COMPLAINT,
                reason="Second complaint, same person.",
            )

    def test_counter_dispute_from_other_party_allowed(self):
        tenant_dispute = open_dispute(
            booking=self.booking,
            opened_by=self.tenant,
            reason_category=DisputeReason.CLEANLINESS,
            reason="Room was dirty.",
        )
        landlord_dispute = open_dispute(
            booking=self.booking,
            opened_by=self.landlord,
            reason_category=DisputeReason.DAMAGED_PROPERTY,
            reason="Tenant damaged furniture.",
        )
        self.assertNotEqual(tenant_dispute.pk, landlord_dispute.pk)
        self.assertEqual(self.booking.disputes.count(), 2)

    def test_clean_is_actually_called_on_save(self):
        with self.assertRaises(ValidationError):
            open_dispute(
                booking=self.booking,
                opened_by=self.tenant,
                reason_category=DisputeReason.CLEANLINESS,
                reason="Too expensive claim.",
                claim_amount=Decimal("999999.00"),
            )

    def test_under_review_status_can_be_saved(self):
        dispute = open_dispute(
            booking=self.booking,
            opened_by=self.tenant,
            reason_category=DisputeReason.CLEANLINESS,
            reason="Under review case.",
        )
        dispute = start_review(dispute=dispute, moderator=self.landlord)
        dispute.refresh_from_db()
        self.assertEqual(dispute.status, DisputeStatus.UNDER_REVIEW)

    def test_status_cannot_skip_under_review(self):
        dispute = open_dispute(
            booking=self.booking,
            opened_by=self.tenant,
            reason_category=DisputeReason.CLEANLINESS,
            reason="Skip attempt.",
        )
        dispute.status = DisputeStatus.RESOLVED_REFUNDED
        dispute.resolved_at = timezone.now()
        dispute.resolved_by = self.landlord
        dispute.resolution_favor = DisputeResolutionFavor.TENANT
        dispute.resolution_amount = Decimal("100.00")
        with self.assertRaises(ValidationError):
            dispute.save()

    def test_status_cannot_go_backwards(self):
        dispute = open_dispute(
            booking=self.booking,
            opened_by=self.tenant,
            reason_category=DisputeReason.CLEANLINESS,
            reason="Backwards attempt.",
        )
        dispute = start_review(dispute=dispute, moderator=self.landlord)
        dispute = resolve_dispute(
            dispute=dispute,
            moderator=self.landlord,
            new_status=DisputeStatus.RESOLVED_REJECTED,
            resolution_favor=DisputeResolutionFavor.LANDLORD,
        )
        dispute.status = DisputeStatus.OPEN
        with self.assertRaises(ValidationError):
            dispute.save()

    def test_resolve_dispute_service_sets_all_resolution_fields(self):
        dispute = open_dispute(
            booking=self.booking,
            opened_by=self.tenant,
            reason_category=DisputeReason.CLEANLINESS,
            reason="Resolve me.",
        )
        dispute = start_review(dispute=dispute, moderator=self.landlord)

        dispute = resolve_dispute(
            dispute=dispute,
            moderator=self.landlord,
            new_status=DisputeStatus.RESOLVED_REFUNDED,
            resolution_favor=DisputeResolutionFavor.TENANT,
            resolution_amount=Decimal("150.00"),
            notes="Partial refund approved.",
        )

        dispute.refresh_from_db()
        self.assertEqual(dispute.status, DisputeStatus.RESOLVED_REFUNDED)
        self.assertIsNotNone(dispute.resolved_at)
        self.assertEqual(dispute.resolved_by, self.landlord)
        self.assertEqual(dispute.resolution_favor, DisputeResolutionFavor.TENANT)
        self.assertEqual(dispute.resolution_amount, Decimal("150.00"))

    def test_resolve_refunded_without_resolution_amount_raises(self):
        dispute = open_dispute(
            booking=self.booking,
            opened_by=self.tenant,
            reason_category=DisputeReason.CLEANLINESS,
            reason="No amount given.",
        )
        dispute = start_review(dispute=dispute, moderator=self.landlord)
        with self.assertRaises(ValidationError):
            resolve_dispute(
                dispute=dispute,
                moderator=self.landlord,
                new_status=DisputeStatus.RESOLVED_REFUNDED,
                resolution_favor=DisputeResolutionFavor.TENANT,
                resolution_amount=None,
            )


class DisputeEvidenceModelTestCase(TestCase):

    def setUp(self):
        self.tenant = User.objects.create_user(
            email="tenant3@example.com", password="securepassword123"
        )
        self.landlord = User.objects.create_user(
            email="landlord3@example.com", password="securepassword123"
        )
        self.stranger = User.objects.create_user(
            email="stranger3@example.com", password="securepassword123"
        )
        self.listing = Listing.objects.create(
            owner=self.landlord,
            title="Evidence Test Listing",
            type=ListingType.APARTMENT,
            address=make_address(city="Munich", street="Marienplatz", house_number="3"),
            max_guests=4,
            current_price=Decimal("1000.00"),
        )
        today = timezone.now().date()
        raw_booking = Booking.objects.create(
            tenant=self.tenant,
            listing=self.listing,
            check_in_date=today + timedelta(days=1),
            check_out_date=today + timedelta(days=3),
            guests_count=2,
            total_price=Decimal("2000.00"),
        )
        self.booking = age_booking_into_dispute_window(raw_booking)
        self.dispute = open_dispute(
            booking=self.booking,
            opened_by=self.tenant,
            reason_category=DisputeReason.CLEANLINESS,
            reason="Needs proof.",
        )

    def test_add_evidence_by_party_success(self):
        evidence = add_evidence(
            dispute=self.dispute,
            uploaded_by=self.tenant,
            url="https://example.com/photo1.jpg",
            description="Dirty kitchen",
        )
        self.assertEqual(self.dispute.evidence.count(), 1)
        self.assertEqual(evidence.uploaded_by, self.tenant)

    def test_add_evidence_by_stranger_raises(self):
        with self.assertRaises(ValidationError):
            add_evidence(
                dispute=self.dispute,
                uploaded_by=self.stranger,
                url="https://example.com/photo2.jpg",
            )

    def test_add_evidence_by_landlord_success(self):
        add_evidence(
            dispute=self.dispute,
            uploaded_by=self.landlord,
            url="https://example.com/counter-evidence.jpg",
        )
        self.assertEqual(self.dispute.evidence.count(), 1)


class AutoCancelDeadlineTestCase(TestCase):
    """Three examples + a "pre-opening" boundary case."""

    def test_deadline_within_business_hours_with_enough_room(self):
        created_at = timezone.make_aware(datetime(2026, 7, 20, 14, 0))
        deadline = calculate_auto_cancel_deadline(created_at)
        self.assertEqual(deadline, timezone.make_aware(datetime(2026, 7, 20, 14, 30)))

    def test_deadline_spills_over_to_next_business_day(self):
        created_at = timezone.make_aware(datetime(2026, 7, 20, 20, 50))
        deadline = calculate_auto_cancel_deadline(created_at)
        self.assertEqual(deadline, timezone.make_aware(datetime(2026, 7, 21, 9, 20)))

    def test_deadline_outside_business_hours_fully_carries_over(self):
        created_at = timezone.make_aware(datetime(2026, 7, 20, 23, 0))
        deadline = calculate_auto_cancel_deadline(created_at)
        self.assertEqual(deadline, timezone.make_aware(datetime(2026, 7, 21, 9, 30)))

    def test_deadline_before_business_hours_starts_accumulating_at_open(self):
        created_at = timezone.make_aware(datetime(2026, 7, 20, 6, 0))
        deadline = calculate_auto_cancel_deadline(created_at)
        self.assertEqual(deadline, timezone.make_aware(datetime(2026, 7, 20, 9, 30)))


class ProcessBookingsCommandTestCase(TestCase):
    """Tests for the `process_bookings` management command (unified cron)."""

    def setUp(self):
        self.landlord = User.objects.create_user(
            email="landlord_cron@test.com", password="pass12345678"
        )
        self.tenant = User.objects.create_user(
            email="tenant_cron@test.com", password="pass12345678"
        )
        self.address = make_address()
        self.listing = Listing.objects.create(
            owner=self.landlord,
            type=ListingType.APARTMENT,
            title="Cron test flat",
            description="A" * 30,
            address=self.address,
            current_price=Decimal("100.00"),
            rental_type="daily",
            max_guests=2,
        )

    def test_overdue_pending_booking_gets_auto_cancelled(self):
        booking = Booking(
            tenant=self.tenant,
            listing=self.listing,
            status=BookingStatus.PENDING,
            check_in_date=timezone.localdate() + timedelta(days=5),
            check_out_date=timezone.localdate() + timedelta(days=7),
            guests_count=1,
            total_price=Decimal("200.00"),
        )
        Booking.objects.bulk_create([booking])
        QuerySet(Booking).filter(id=booking.id).update(
            created_at=timezone.now() - timedelta(days=1)
        )

        call_command("process_bookings")

        booking.refresh_from_db()
        self.assertEqual(booking.status, BookingStatus.AUTO_CANCELLED)
        self.assertIsNotNone(booking.cancelled_at)

    def test_recent_pending_booking_not_touched(self):
        booking = Booking.objects.create(
            tenant=self.tenant,
            listing=self.listing,
            status=BookingStatus.PENDING,
            check_in_date=timezone.localdate() + timedelta(days=5),
            check_out_date=timezone.localdate() + timedelta(days=7),
            guests_count=1,
            total_price=Decimal("200.00"),
        )
        call_command("process_bookings")
        booking.refresh_from_db()
        self.assertEqual(booking.status, BookingStatus.PENDING)

    def test_confirmed_booking_past_checkout_gets_completed(self):
        booking = Booking(
            tenant=self.tenant,
            listing=self.listing,
            status=BookingStatus.CONFIRMED,
            check_in_date=timezone.localdate() - timedelta(days=5),
            check_out_date=timezone.localdate() - timedelta(days=1),
            guests_count=1,
            total_price=Decimal("200.00"),
        )
        Booking.objects.bulk_create([booking])

        call_command("process_bookings")

        booking.refresh_from_db()
        self.assertEqual(booking.status, BookingStatus.COMPLETED)

    def test_confirmed_booking_future_checkout_not_touched(self):
        booking = Booking.objects.create(
            tenant=self.tenant,
            listing=self.listing,
            status=BookingStatus.CONFIRMED,
            check_in_date=timezone.localdate() + timedelta(days=5),
            check_out_date=timezone.localdate() + timedelta(days=7),
            guests_count=1,
            total_price=Decimal("200.00"),
        )
        call_command("process_bookings")
        booking.refresh_from_db()
        self.assertEqual(booking.status, BookingStatus.CONFIRMED)


class BookingCreateValidationApiTestCase(TestCase):
    """Regression: POST /bookings/ was returning a 500 error instead of a 400.

    `BookingService.create_booking` calls `booking.save()` (which triggers `full_clean()`),
    but DRF does not automatically convert `django.core.exceptions.ValidationError` into an HTTP response.
    Business rules validated exclusively within `Booking.clean()` (such as guest capacity
    and duration limits) were therefore resulting in an unhandled exception.
    """

    def setUp(self):
        self.landlord = User.objects.create_user(email="landlord@example.com", password="x")
        self.tenant = User.objects.create_user(email="tenant@example.com", password="x")
        address = Address.objects.create(
            region="Saarland",
            city="Saarlouis",
            street="Kaiser-Wilhelm-Straße",
            house_number="12",
            postal_code="66740",
        )
        self.listing = Listing.objects.create(
            owner=self.landlord,
            address=address,
            status=ListingStatus.PUBLISHED,
            is_active=True,
            type=ListingType.APARTMENT,
            rental_type=RentalType.ANY,
            title="Regression listing",
            description="d",
            max_guests=2,
            current_price=Decimal("100.00"),
        )
        today = timezone.now().date()
        PriceHistory.objects.create(
            listing=self.listing,
            price=Decimal("100.00"),
            valid_from=today,
            changed_by=self.landlord,
        )
        # raise_request_exception=False: an unhandled exception in a view
        # should manifest as a 500 (see assertion below), rather than as a test exception.
        self.client = APIClient(raise_request_exception=False)
        self.client.force_authenticate(self.tenant)

    def _payload(self, *, nights=3, guests=2):
        check_in = timezone.now().date() + timedelta(days=5)
        return {
            "listing_id": str(self.listing.pk),
            "check_in_date": check_in.isoformat(),
            "check_out_date": (check_in + timedelta(days=nights)).isoformat(),
            "guests_count": guests,
        }

    def test_valid_booking_is_created(self):
        response = self.client.post("/api/v1/bookings/", self._payload(), format="json")

        self.assertEqual(response.status_code, 201, response.content)

    def test_guests_over_capacity_returns_400_not_500(self):
        response = self.client.post("/api/v1/bookings/", self._payload(guests=10), format="json")

        self.assertEqual(response.status_code, 400, response.content)

    def test_duration_over_maximum_returns_400_not_500(self):
        response = self.client.post(
            "/api/v1/bookings/", self._payload(nights=400), format="json"
        )

        self.assertEqual(response.status_code, 400, response.content)


class UserGuardTestCase(TestCase):
    """Regression: The owner's public profile should be accessible to a renter who has an
    active (`pending`/`confirmed`) OR completed booking.

    Previously, `COMPLETED_OR_ACTIVE_STATUSES` was defined as a nested tuple—`((PENDING,
    CONFIRMED), COMPLETED)`—which meant that `status__in` effectively matched only
    `completed`.
    """

    def setUp(self):
        self.landlord = User.objects.create_user(email="landlord@example.com", password="x")
        self.tenant = User.objects.create_user(email="tenant@example.com", password="x")
        address = Address.objects.create(
            region="Saarland",
            city="Saarlouis",
            street="Kaiser-Wilhelm-Straße",
            house_number="12",
            postal_code="66740",
        )
        self.listing = Listing.objects.create(
            owner=self.landlord,
            address=address,
            status=ListingStatus.PUBLISHED,
            is_active=True,
            type=ListingType.APARTMENT,
            rental_type=RentalType.ANY,
            title="Guard listing",
            description="d",
            max_guests=2,
            current_price=Decimal("100.00"),
        )

    def _booking_with_status(self, status):
        Booking.objects.all().delete()
        today = timezone.now().date()
        booking = Booking.objects.create(
            tenant=self.tenant,
            listing=self.listing,
            check_in_date=today + timedelta(days=5),
            check_out_date=today + timedelta(days=8),
            guests_count=1,
            total_price=Decimal("300.00"),
        )

        # set the status by bypassing clean(), since we need "completed" bookings.
        Booking.objects.filter(pk=booking.pk).update(status=status)

    def test_status_constant_is_flat(self):
        self.assertTrue(all(isinstance(s, str) for s in COMPLETED_OR_ACTIVE_STATUSES))
        self.assertEqual(
            set(COMPLETED_OR_ACTIVE_STATUSES),
            {BookingStatus.PENDING, BookingStatus.CONFIRMED, BookingStatus.COMPLETED},
        )

    def test_access_granted_for_pending_confirmed_and_completed(self):
        for status in (BookingStatus.PENDING, BookingStatus.CONFIRMED, BookingStatus.COMPLETED):
            with self.subTest(status=status):
                self._booking_with_status(status)
                self.assertTrue(
                    user_has_completed_booking_with_listing_owner(self.tenant, self.landlord.pk)
                )

    def test_access_denied_for_cancelled_and_rejected(self):
        for status in (
            BookingStatus.REJECTED,
            BookingStatus.CANCELLED_BY_TENANT,
            BookingStatus.CANCELLED_BY_LANDLORD,
        ):
            with self.subTest(status=status):
                self._booking_with_status(status)
                self.assertFalse(
                    user_has_completed_booking_with_listing_owner(self.tenant, self.landlord.pk)
                )

    def test_access_denied_without_any_booking(self):
        Booking.objects.all().delete()
        self.assertFalse(
            user_has_completed_booking_with_listing_owner(self.tenant, self.landlord.pk)
        )


class CancellationReasonCodeTestCase(TestCase):
    def test_code_outside_seed_enum_is_valid(self):
        CancellationReason(
            code="LATE_ARRIVAL", description="Guest arrives too late"
        ).full_clean()

    def test_duplicate_code_fails_on_uniqueness(self):
        CancellationReason.objects.create(code="LATE_ARRIVAL", description="x")
        with self.assertRaises(ValidationError) as ctx:
            CancellationReason(code="LATE_ARRIVAL", description="y").full_clean()
        self.assertIn("already exists", str(ctx.exception.message_dict["code"]))

    def test_invalid_code_format_is_rejected(self):
        for bad in ("lowercase", "With Space", "HAS_DIGIT_1", "E2E_REASON"):
            with self.subTest(code=bad):
                with self.assertRaises(ValidationError) as ctx:
                    CancellationReason(code=bad, description="x").full_clean()
                self.assertIn("code", ctx.exception.message_dict)

    def test_seeded_codes_are_uppercase_and_match_their_own_validation(self):
        for reason in StandardCancellationReason:
            with self.subTest(code=reason.name):
                seeded = CancellationReason.objects.get(code=reason.name)
                seeded.full_clean()


class UppercaseCodesMigrationTestCase(TestCase):
    """Data migration for bookings.0004: in existing, deployed databases, seed codes are stored in
    lowercase (`changed_plans`), whereas the signal now generates `CHANGED_PLANS`. Without a
    migration, this would have resulted in duplicates in the production environment."""

    def setUp(self):
        import importlib

        from django.apps import apps

        self.apps = apps
        self.migration = importlib.import_module(
            "apps.bookings.migrations.0003_uppercase_standard_cancellation_reason_codes"
        )
        # "Pre-migration" state: only old codes exist in the database. A standard QuerySet performs
        # a physical deletion, regardless of the manager implementation. We cannot use
        # `all_objects.all().delete()` here: following the PR that switched `all_objects` to
        # `SoftDeleteQuerySet`, this would result in a soft delete, and the rows would remain in the table.
        QuerySet(CancellationReason).delete()

    def test_lowercase_code_is_renamed_in_place(self):
        old = CancellationReason.objects.create(code="LATE", description="legacy")
        CancellationReason.objects.filter(pk=old.pk).update(code="changed_plans")

        self.migration.to_uppercase(self.apps, None)

        old.refresh_from_db()
        self.assertEqual(old.code, "CHANGED_PLANS")
        self.assertEqual(CancellationReason.all_objects.count(), 1)

    def test_duplicate_is_removed_when_both_variants_exist(self):
        old = CancellationReason.objects.create(code="LATE", description="legacy")
        CancellationReason.objects.filter(pk=old.pk).update(code="changed_plans")
        new = CancellationReason.objects.create(code="CHANGED_PLANS", description="new")

        self.migration.to_uppercase(self.apps, None)

        # In the model migration itself, `delete()` performs a physical deletion; however,
        # this is a model that uses soft deletes, so we only check the "active"
        # (non-deleted) records.
        self.assertEqual(list(CancellationReason.objects.values_list("pk", flat=True)), [new.pk])

    def test_migration_is_idempotent(self):
        CancellationReason.objects.create(code="CHANGED_PLANS", description="new")

        self.migration.to_uppercase(self.apps, None)
        self.migration.to_uppercase(self.apps, None)

        self.assertEqual(CancellationReason.all_objects.count(), 1)
