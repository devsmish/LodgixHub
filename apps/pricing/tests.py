from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.listings.choices import ListingType
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


class PriceHistoryTest(TestCase):
    def setUp(self):
        self.landlord = User.objects.create_user(
            email="landlord@example.com", password="securepassword123"
        )
        self.listing = Listing.objects.create(
            owner=self.landlord,
            title="Test Hotel",
            type=ListingType.HOTEL,
            address=make_address(),
            max_guests=2,
            current_price=Decimal("100.00"),
        )
        self.today = timezone.now().date()

    def test_price_history_past_date_raises(self):
        past_date = self.today - timedelta(days=1)
        history = PriceHistory(
            listing=self.listing,
            price=100,
            valid_from=past_date,
            changed_by=self.landlord,
        )
        with self.assertRaises(ValidationError):
            history.full_clean()

    def test_first_price_effective_today_is_allowed(self):
        history = PriceHistory.objects.create(
            listing=self.listing,
            price=100,
            valid_from=self.today,
            changed_by=self.landlord,
        )
        self.assertEqual(history.price, Decimal("100.00"))

    def test_second_price_effective_today_raises(self):
        PriceHistory.objects.create(
            listing=self.listing,
            price=100,
            valid_from=self.today,
            changed_by=self.landlord,
        )
        with self.assertRaises(ValidationError):
            PriceHistory.objects.create(
                listing=self.listing,
                price=150,
                valid_from=self.today,
                changed_by=self.landlord,
            )

    def test_future_price_after_first_is_allowed(self):
        PriceHistory.objects.create(
            listing=self.listing,
            price=100,
            valid_from=self.today,
            changed_by=self.landlord,
        )
        future = PriceHistory.objects.create(
            listing=self.listing,
            price=120,
            valid_from=self.today + timedelta(days=3),
            changed_by=self.landlord,
        )
        self.assertEqual(future.price, Decimal("120.00"))

    def test_negative_or_zero_price_raises(self):
        history = PriceHistory(
            listing=self.listing,
            price=Decimal("0.00"),
            valid_from=self.today,
            changed_by=self.landlord,
        )
        with self.assertRaises(ValidationError):
            history.full_clean()

    def test_xor_listing_or_room_constraint(self):
        history = PriceHistory(
            price=100, valid_from=self.today, changed_by=self.landlord
        )
        with self.assertRaises(ValidationError):
            history.full_clean()

    def test_multiple_rows_same_valid_from_are_kept_not_overwritten(self):
        future_date = self.today + timedelta(days=5)
        PriceHistory.objects.create(
            listing=self.listing,
            price=100,
            valid_from=self.today,
            changed_by=self.landlord,
        )
        PriceHistory.objects.create(
            listing=self.listing,
            price=130,
            valid_from=future_date,
            changed_by=self.landlord,
        )
        corrected = PriceHistory.objects.create(
            listing=self.listing,
            price=140,
            valid_from=future_date,
            changed_by=self.landlord,
        )

        same_date_rows = PriceHistory.objects.filter(
            listing=self.listing, valid_from=future_date
        )
        self.assertEqual(same_date_rows.count(), 2)

        latest = same_date_rows.order_by("-created_at").first()
        self.assertEqual(latest.pk, corrected.pk)
        self.assertEqual(latest.price, Decimal("140.00"))

    def test_log_model_immutability(self):
        entry = PriceHistory.objects.create(
            listing=self.listing,
            price=100,
            valid_from=self.today,
            changed_by=self.landlord,
        )
        entry.price = 500
        with self.assertRaises(ValidationError):
            entry.save()

    def test_bulk_delete_still_protected(self):
        PriceHistory.objects.create(
            listing=self.listing,
            price=100,
            valid_from=self.today,
            changed_by=self.landlord,
        )
        with self.assertRaises(ValidationError):
            PriceHistory.objects.filter(listing=self.listing).delete()

    def test_effective_on_picks_max_valid_from_not_exceeding_date(self):
        PriceHistory.objects.create(
            listing=self.listing,
            price=100,
            valid_from=self.today,
            changed_by=self.landlord,
        )
        PriceHistory.objects.create(
            listing=self.listing,
            price=120,
            valid_from=self.today + timedelta(days=5),
            changed_by=self.landlord,
        )

        far_future = self.today + timedelta(days=2)
        effective = PriceHistory.objects.effective_on(
            far_future, listing=self.listing
        ).first()

        self.assertEqual(effective.price, Decimal("100.00"))

    def test_effective_on_breaks_ties_by_created_at(self):
        future_date = self.today + timedelta(days=5)
        PriceHistory.objects.create(
            listing=self.listing,
            price=100,
            valid_from=self.today,
            changed_by=self.landlord,
        )
        PriceHistory.objects.create(
            listing=self.listing,
            price=130,
            valid_from=future_date,
            changed_by=self.landlord,
        )
        corrected = PriceHistory.objects.create(
            listing=self.listing,
            price=140,
            valid_from=future_date,
            changed_by=self.landlord,
        )

        effective = PriceHistory.objects.effective_on(
            future_date, listing=self.listing
        ).first()

        self.assertEqual(effective.pk, corrected.pk)
        self.assertEqual(effective.price, Decimal("140.00"))

    def test_effective_on_returns_none_before_any_price_exists(self):
        future_listing = Listing.objects.create(
            owner=self.landlord,
            title="No Price Yet",
            type=ListingType.HOTEL,
            address=make_address(city="Munich", street="Marienplatz", house_number="1"),
            max_guests=2,
            current_price=Decimal("50.00"),
        )
        effective = PriceHistory.objects.effective_on(
            self.today, listing=future_listing
        ).first()
        self.assertIsNone(effective)


class UpdateListingCurrentPriceCommandTestCase(TestCase):
    """Tests for the update_listing_current_price - management command (daily cron job)."""

    def setUp(self):
        self.landlord = User.objects.create_user(
            email="landlord_price_cron@test.com", password="pass12345678"
        )
        self.address = make_address()
        self.listing = Listing.objects.create(
            owner=self.landlord,
            type=ListingType.APARTMENT,
            title="Price cron flat",
            description="A" * 30,
            address=self.address,
            current_price=Decimal("100.00"),
            rental_type="daily",
            max_guests=2,
        )

    def test_updates_cache_from_latest_effective_price(self):
        price = PriceHistory(
            listing=self.listing,
            price=Decimal("150.00"),
            valid_from=timezone.localdate() - timedelta(days=1),
            changed_by=self.landlord,
        )
        PriceHistory.objects.bulk_create([price])

        call_command("update_listing_current_price")

        self.listing.refresh_from_db()
        self.assertEqual(self.listing.current_price, Decimal("150.00"))

    def test_does_not_touch_cache_when_no_new_price(self):
        call_command("update_listing_current_price")
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.current_price, Decimal("100.00"))

    def test_ignores_future_price(self):
        PriceHistory.objects.create(
            listing=self.listing,
            price=Decimal("999.00"),
            valid_from=timezone.localdate() + timedelta(days=5),
            changed_by=self.landlord,
        )
        call_command("update_listing_current_price")
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.current_price, Decimal("100.00"))
