from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.bookings.choices import (
    BookingStatus,
    DisputeReason,
    DisputeStatus,
    StandardCancellationReason,
)
from apps.bookings.models import Booking, CancellationReason, Dispute
from apps.bookings.services import resolve_dispute
from apps.listings.choices import ListingType
from apps.listings.models import Address, Listing

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


class CancellationReasonModelTestCase(TestCase):

    def test_str_returns_description(self):
        reason = CancellationReason.objects.create(
            code=StandardCancellationReason.CHANGED_PLANS,
            description="Changed plans",
        )
        self.assertEqual(str(reason), "Changed plans")

    def test_code_uniqueness(self):
        CancellationReason.objects.create(
            code=StandardCancellationReason.CHANGED_PLANS, description="A"
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CancellationReason.objects.create(
                    code=StandardCancellationReason.CHANGED_PLANS, description="B"
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
        Dispute.objects.create(
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
        self.listing = Listing.objects.create(
            owner=self.landlord,
            title="Dispute Test Listing",
            type=ListingType.APARTMENT,
            address=make_address(
                city="Berlin", street="Alexanderplatz", house_number="1"
            ),
            max_guests=4,
            current_price=Decimal("1000.00"),
        )
        today = timezone.now().date()
        self.booking = Booking.objects.create(
            tenant=self.tenant,
            listing=self.listing,
            check_in_date=today + timedelta(days=1),
            check_out_date=today + timedelta(days=3),
            guests_count=2,
            total_price=Decimal("2000.00"),
        )

    def test_create_open_dispute(self):
        dispute = Dispute.objects.create(
            booking=self.booking,
            opened_by=self.tenant,
            reason_category=DisputeReason.CLEANLINESS,
            reason="Not clean.",
        )
        self.assertEqual(dispute.status, DisputeStatus.OPEN)

    def test_clean_is_actually_called_on_save(self):
        with self.assertRaises(ValidationError):
            Dispute.objects.create(
                booking=self.booking,
                opened_by=self.tenant,
                reason_category=DisputeReason.CLEANLINESS,
                reason="Too expensive claim.",
                claim_amount=Decimal("999999.00"),
            )

    def test_under_review_status_can_be_saved(self):
        dispute = Dispute.objects.create(
            booking=self.booking,
            opened_by=self.tenant,
            reason_category=DisputeReason.CLEANLINESS,
            reason="Under review case.",
        )
        dispute.status = DisputeStatus.UNDER_REVIEW
        dispute.save()
        dispute.refresh_from_db()
        self.assertEqual(dispute.status, DisputeStatus.UNDER_REVIEW)

    def test_resolve_dispute_service_sets_resolved_at(self):
        dispute = Dispute.objects.create(
            booking=self.booking,
            opened_by=self.tenant,
            reason_category=DisputeReason.CLEANLINESS,
            reason="Resolve me.",
        )

        resolve_dispute(dispute, DisputeStatus.RESOLVED_REFUNDED)

        dispute.refresh_from_db()
        self.assertEqual(dispute.status, DisputeStatus.RESOLVED_REFUNDED)
        self.assertIsNotNone(dispute.resolved_at)

    def test_resolve_dispute_service_rejected_sets_resolved_at_too(self):
        dispute = Dispute.objects.create(
            booking=self.booking,
            opened_by=self.tenant,
            reason_category=DisputeReason.CLEANLINESS,
            reason="Resolve me too.",
        )

        resolve_dispute(dispute, DisputeStatus.RESOLVED_REJECTED)

        dispute.refresh_from_db()
        self.assertIsNotNone(dispute.resolved_at)
