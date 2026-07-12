from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.bookings.choices import BookingStatus
from apps.bookings.constants import REVIEW_WINDOW_DAYS
from apps.bookings.models import Booking
from apps.listings.choices import ListingType
from apps.listings.models import Address, Listing
from apps.reviews.choices import ReviewStatus
from apps.reviews.models import Review

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


def make_completed_booking(*, tenant, listing, days_since_checkout=1):
    today = timezone.now().date()
    check_in = today - timedelta(days=5 + days_since_checkout)
    check_out = today - timedelta(days=days_since_checkout)
    booking = Booking.objects.create(
        tenant=tenant,
        listing=listing,
        check_in_date=today + timedelta(days=1),
        check_out_date=today + timedelta(days=3),
        guests_count=2,
        total_price=Decimal("2000.00"),
    )
    Booking.objects.filter(pk=booking.pk).update(
        status=BookingStatus.COMPLETED,
        check_in_date=check_in,
        check_out_date=check_out,
    )
    booking.refresh_from_db()
    return booking


class ReviewModelTestCase(TestCase):

    def setUp(self):
        self.tenant = User.objects.create_user(
            email="tenant@example.com", password="securepassword123"
        )
        self.other_user = User.objects.create_user(
            email="stranger@example.com", password="securepassword123"
        )
        self.landlord = User.objects.create_user(
            email="landlord@example.com", password="securepassword123"
        )
        self.listing = Listing.objects.create(
            owner=self.landlord,
            title="Review Test Listing",
            type=ListingType.APARTMENT,
            address=make_address(),
            max_guests=4,
            current_price=Decimal("1000.00"),
        )
        self.booking = make_completed_booking(tenant=self.tenant, listing=self.listing)

    def test_create_valid_review(self):
        review = Review.objects.create(
            booking=self.booking,
            author=self.tenant,
            rating=5,
            comment="Absolutely wonderful stay, highly recommended!",
        )
        self.assertEqual(review.status, ReviewStatus.PENDING)
        self.assertEqual(review.listing, self.listing)

    def test_review_on_non_completed_booking_raises(self):
        pending_booking = Booking.objects.create(
            tenant=self.tenant,
            listing=self.listing,
            check_in_date=timezone.now().date() + timedelta(days=1),
            check_out_date=timezone.now().date() + timedelta(days=3),
            guests_count=2,
            total_price=Decimal("2000.00"),
        )
        with self.assertRaises(ValidationError):
            Review.objects.create(
                booking=pending_booking,
                author=self.tenant,
                rating=5,
                comment="Too early to review this one.",
            )

    def test_review_after_window_raises(self):
        old_booking = make_completed_booking(
            tenant=self.tenant,
            listing=self.listing,
            days_since_checkout=REVIEW_WINDOW_DAYS + 5,
        )
        with self.assertRaises(ValidationError):
            Review.objects.create(
                booking=old_booking,
                author=self.tenant,
                rating=4,
                comment="This window has long closed by now.",
            )

    def test_review_by_non_tenant_raises(self):
        with self.assertRaises(ValidationError):
            Review.objects.create(
                booking=self.booking,
                author=self.other_user,
                rating=3,
                comment="Not my booking, but I'll review it anyway.",
            )

    def test_rating_out_of_range_raises(self):
        with self.assertRaises(ValidationError):
            Review.objects.create(
                booking=self.booking,
                author=self.tenant,
                rating=6,
                comment="Rating way too high for the 1-5 scale.",
            )

    def test_comment_too_short_raises(self):
        with self.assertRaises(ValidationError):
            Review.objects.create(
                booking=self.booking,
                author=self.tenant,
                rating=4,
                comment="short",
            )

    def test_comment_blank_is_allowed(self):
        review = Review.objects.create(
            booking=self.booking, author=self.tenant, rating=4, comment=""
        )
        self.assertEqual(review.comment, "")

    def test_duplicate_review_same_booking_raises(self):
        Review.objects.create(
            booking=self.booking,
            author=self.tenant,
            rating=5,
            comment="First review on this booking.",
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Review.objects.create(
                    booking=self.booking,
                    author=self.tenant,
                    rating=3,
                    comment="Trying to review the same booking twice.",
                )

    def test_hard_delete_actually_removes_row(self):
        review = Review.objects.create(
            booking=self.booking,
            author=self.tenant,
            rating=5,
            comment="This review will be deleted shortly.",
        )
        review_id = review.id
        review.delete()
        self.assertFalse(Review.objects.filter(pk=review_id).exists())

    def test_rebooking_same_listing_allows_new_review(self):
        Review.objects.create(
            booking=self.booking,
            author=self.tenant,
            rating=5,
            comment="First stay was great.",
        )
        second_booking = make_completed_booking(
            tenant=self.tenant, listing=self.listing
        )
        second_review = Review.objects.create(
            booking=second_booking,
            author=self.tenant,
            rating=4,
            comment="Second stay was good too.",
        )
        self.assertNotEqual(second_review.booking_id, self.booking.id)


class ListingRatingRecalculationTestCase(TestCase):

    def setUp(self):
        self.tenant = User.objects.create_user(
            email="tenant2@example.com", password="securepassword123"
        )
        self.landlord = User.objects.create_user(
            email="landlord2@example.com", password="securepassword123"
        )
        self.listing = Listing.objects.create(
            owner=self.landlord,
            title="Rating Test Listing",
            type=ListingType.APARTMENT,
            address=make_address(
                city="Berlin", street="Alexanderplatz", house_number="1"
            ),
            max_guests=4,
            current_price=Decimal("1000.00"),
        )

    def _make_review(
        self, rating, status=ReviewStatus.PUBLISHED, days_since_checkout=1
    ):
        booking = make_completed_booking(
            tenant=self.tenant,
            listing=self.listing,
            days_since_checkout=days_since_checkout,
        )
        review = Review.objects.create(
            booking=booking,
            author=self.tenant,
            rating=rating,
            comment="Review used purely for rating aggregation tests.",
        )
        if status != ReviewStatus.PENDING:
            review.status = status
            review.save()
        return review

    def test_rating_avg_updates_on_create(self):
        self._make_review(4)
        self._make_review(5, days_since_checkout=2)

        self.listing.refresh_from_db()
        self.assertEqual(self.listing.reviews_count, 2)
        self.assertEqual(self.listing.rating_avg, Decimal("4.50"))

    def test_pending_reviews_excluded_from_average(self):
        self._make_review(5, status=ReviewStatus.PENDING)
        self._make_review(1, status=ReviewStatus.PUBLISHED, days_since_checkout=2)

        self.listing.refresh_from_db()
        self.assertEqual(self.listing.reviews_count, 1)
        self.assertEqual(self.listing.rating_avg, Decimal("1.00"))

    def test_rating_avg_updates_on_delete(self):
        review = self._make_review(5)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.reviews_count, 1)

        review.delete()

        self.listing.refresh_from_db()
        self.assertEqual(self.listing.reviews_count, 0)
        self.assertEqual(self.listing.rating_avg, Decimal("0.00"))

    def test_rating_avg_updates_when_status_changes(self):
        review = self._make_review(3, status=ReviewStatus.PENDING)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.reviews_count, 0)

        review.status = ReviewStatus.PUBLISHED
        review.save()

        self.listing.refresh_from_db()
        self.assertEqual(self.listing.reviews_count, 1)
        self.assertEqual(self.listing.rating_avg, Decimal("3.00"))
