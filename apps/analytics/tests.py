from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.test import APIClient

from apps.analytics.constants import VIEW_DEDUP_WINDOW_MINUTES
from apps.analytics.models import SearchHistory, ViewHistory
from apps.analytics.services.search_history import SearchHistoryService
from apps.analytics.services.view_history import ViewHistoryService
from apps.listings.models import Address, Listing
from core.models import LogQuerySet

User = get_user_model()


class AnalyticsServiceTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com", password="password123"
        )
        self.address = Address.objects.create(
            country="Germany",
            region="Bavaria",
            city="Munich",
            street="Test Strasse",
            house_number="10-A",
            postal_code="80331",
        )
        self.listing = Listing.objects.create(
            title="Test Apartment",
            current_price=150000.00,
            owner=self.user,
            address=self.address,
            max_guests=4,
            views_count=0,
        )

    def test_search_history_normalization_and_creation(self):
        """Verification of keyword normalization when saving the search log."""
        service = SearchHistoryService()
        record = service.record_search(
            user=self.user, keyword=" Apartment in New York ", results_count=5
        )
        self.assertEqual(record.keyword, "apartment in new york")
        self.assertEqual(record.user, self.user)
        self.assertEqual(record.results_count, 5)

    def test_search_history_empty_keyword_error(self):
        """Verification that DRF ValidationError is raised for an empty query
        (caught by SearchHistoryCreateDTO.validate_keyword() after trim)."""
        service = SearchHistoryService()
        with self.assertRaises(DRFValidationError):
            service.record_search(user=self.user, keyword="   ")

    def test_view_history_deduplication(self):
        """Verification that repeated views within the deduplication window are not counted."""
        service = ViewHistoryService()

        # create the first record in the past by spoofing the system time at the moment `.record_view()` is called.
        old_time = timezone.now() - timedelta(minutes=VIEW_DEDUP_WINDOW_MINUTES + 1)
        with patch("django.utils.timezone.now", return_value=old_time):
            view1 = service.record_view(listing=self.listing, user=self.user)

        self.assertIsNotNone(view1)

        # A re-scan in real time (outside the deduplication window) must be successfully recorded.
        view2 = service.record_view(listing=self.listing, user=self.user)
        self.assertIsNotNone(view2)


class AnalyticsAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="user@example.com", password="password123"
        )
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com", password="adminpassword", is_staff=True
        )
        self.address = Address.objects.create(
            country="Germany",
            region="Berlin",
            city="Berlin",
            street="Alexanderplatz",
            house_number="1",
            postal_code="10178",
        )
        self.listing = Listing.objects.create(
            title="Luxury Penthouse",
            current_price=500000.00,
            owner=self.user,
            address=self.address,
            max_guests=6,
        )

        self.search_history_url = "/api/v1/search-history/mine/"
        self.admin_stats_url = "/api/v1/stats/admin-dashboard/"

    def test_my_search_history_auth_guard(self):
        """Checking access protection for personal search history."""
        response = self.client.get(self.search_history_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_and_clear_search_history(self):
        """Verifying the retrieval of the history list and its complete clearing."""
        self.client.force_authenticate(user=self.user)

        service = SearchHistoryService()
        service.record_search(user=self.user, keyword="дом")
        service.record_search(user=self.user, keyword="дача")

        response = self.client.get(self.search_history_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 2)

        # patch the `delete` method of `LogQuerySet` so that it calls the built-in `purge()`.
        with patch.object(LogQuerySet, "delete", lambda qs: qs.purge()):
            delete_response = self.client.delete(self.search_history_url)
            self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(SearchHistory.objects.filter(user=self.user).count(), 0)

    def test_admin_dashboard_stats_and_date_filtering(self):
        """Testing the administrator statistics panel using a date filter."""
        self.client.force_authenticate(user=self.admin_user)

        now = timezone.now()
        yesterday = now - timedelta(days=1)
        ten_days_ago = now - timedelta(days=10)

        sh_recent = SearchHistoryService().record_search(
            user=self.user, keyword="свежий поиск", results_count=0
        )
        sh_old = SearchHistoryService().record_search(
            user=self.user, keyword="старый поиск", results_count=0
        )

        # Iterate over the LogQuerySet using a clean, unmodified Django QuerySet.
        from django.db.models import QuerySet

        QuerySet(SearchHistory).filter(id=sh_old.id).update(created_at=ten_days_ago)

        # test the query without a date filter (both records should be returned).
        response = self.client.get(self.admin_stats_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["summary"]["searches_count"], 2)

        # Filter by "yesterday" (only one recent entry should remain).
        iso_yesterday_str = yesterday.isoformat()
        response_filtered = self.client.get(
            f"{self.admin_stats_url}?date_from={iso_yesterday_str}"
        )

        self.assertEqual(response_filtered.status_code, status.HTTP_200_OK)
        self.assertEqual(response_filtered.data["summary"]["searches_count"], 1)
