from decimal import Decimal

from django.db.models import Count, Sum

from apps.analytics.filters import apply_date_range
from apps.analytics.models import SearchHistory, ViewHistory
from apps.bookings.choices import BookingStatus
from apps.bookings.models import Booking
from apps.listings.models import Listing
from apps.users.models import User


class AdminDashboardStatsService:
    """GET /api/v1/stats/admin-dashboard/ — aggregated summary."""

    def get_summary(self, *, date_from=None, date_to=None):
        search_qs = apply_date_range(SearchHistory.objects.all(), date_from, date_to)
        view_qs = apply_date_range(ViewHistory.objects.all(), date_from, date_to)

        return {
            "period": {"date_from": date_from, "date_to": date_to},
            "platform_summary": self._get_platform_summary(),
            "summary": {
                "searches_count": search_qs.count(),
                "views_count": view_qs.count(),
            },
            "gap_analysis": self._get_gap_analysis(search_qs),
            "top_trending_listings": self._get_top_trending_listings(view_qs),
        }

    @staticmethod
    def _get_platform_summary():
        """Returns the total number of users, listings (by type), and bookings (by status),
        as well as the sum of `final_price` for completed bookings. A snapshot of the platform's
        current state—independent of `date_from` or `date_to`."""

        listings_by_type = {
            row["type"]: row["count"]
            for row in Listing.objects.values("type").annotate(count=Count("id"))
        }
        bookings_by_status = {
            row["status"]: row["count"]
            for row in Booking.objects.values("status").annotate(count=Count("id"))
        }
        completed_revenue = Booking.objects.filter(
            status=BookingStatus.COMPLETED
        ).aggregate(total=Sum("total_price"))["total"] or Decimal("0.00")

        return {
            "total_users": User.objects.count(),
            "listings_by_type": listings_by_type,
            "bookings_by_status": bookings_by_status,
            "completed_bookings_revenue": completed_revenue,
        }

    @staticmethod
    def _get_gap_analysis(search_qs):
        gap_searches_qs = search_qs.filter(results_count=0)
        recent = gap_searches_qs.order_by("-created_at")[:10]
        return {
            "total_zero_result_searches": gap_searches_qs.count(),
            "recent_zero_result_searches": [
                {
                    "keyword": s.keyword,
                    "user": s.user.email if s.user else None,
                    "created_at": s.created_at,
                }
                for s in recent
            ],
        }

    @staticmethod
    def _get_top_trending_listings(view_qs):
        return list(
            view_qs.values("listing_id", "listing__title")
            .annotate(views_count=Count("id"))
            .order_by("-views_count")[:5]
        )
