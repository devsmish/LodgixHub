from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.listings.models import Listing
from apps.pricing.models import PriceHistory

User = get_user_model()


class PriceHistoryTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(email="test@example.com")
        self.listing = Listing.objects.create(
            owner=self.user,
            title="Test Hotel",
            type="hotel",
            latitude=0.0,
            longitude=0.0,
            max_guests=2,
            price_per_night=100.0,
        )
        self.today = timezone.now().date()

    def test_price_history_future_date_validation(self):
        # The Ban on the Past
        past_date = self.today - timedelta(days=1)
        history = PriceHistory(
            listing=self.listing, price=100, effective_date=past_date
        )
        with self.assertRaises(ValidationError):
            history.full_clean()

    def test_price_history_overwrite_logic(self):
        # Verification of record (register) merging
        PriceHistory.objects.create(
            listing=self.listing, price=100, effective_date=self.today
        )
        PriceHistory.objects.create(
            listing=self.listing, price=200, effective_date=self.today
        )

        self.assertEqual(PriceHistory.objects.filter(listing=self.listing).count(), 1)
        self.assertEqual(PriceHistory.objects.get(listing=self.listing).price, 200)

    def test_log_model_immutability(self):
        # Verification that LogModel blocks the update
        entry = PriceHistory.objects.create(
            listing=self.listing, price=100, effective_date=self.today
        )
        entry.price = 500
        with self.assertRaises(ValidationError):
            entry.save()
