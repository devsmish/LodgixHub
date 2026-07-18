from django.db.models import Count
# from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import status, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.filters import apply_date_range
from apps.analytics.models import SearchHistory, ViewHistory
from apps.security.permissions import IsAdmin


class AdminDashboardStatsView(APIView):
    """
    GET /api/analytics/admin/stats/
    Returns aggregated analytics for the admin panel.
    Supports date filtering via query parameters `?date_from=...` and `?date_to=...`.
    Access: administrators only.
    """

    permission_classes = [IsAdmin]

    @extend_schema(
        responses={
            200: inline_serializer(
                name="AdminDashboardStatsResponse",
                fields={
                    "period": inline_serializer(
                        name="StatsPeriod",
                        fields={
                            "date_from": serializers.CharField(allow_null=True),
                            "date_to": serializers.CharField(allow_null=True),
                        }
                    ),
                    "summary": inline_serializer(
                        name="StatsSummary",
                        fields={
                            "searches_count": serializers.IntegerField(),
                            "views_count": serializers.IntegerField(),
                        }
                    ),
                    "gap_analysis": inline_serializer(
                        name="StatsGapAnalysis",
                        fields={
                            "total_zero_result_searches": serializers.IntegerField(),
                            "recent_zero_result_searches": serializers.ListField(child=serializers.DictField()),
                        }
                    ),
                    "top_trending_listings": serializers.ListField(child=serializers.DictField()),
                }
            )
        }
    )
    # @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        search_qs = SearchHistory.objects.all()
        view_qs = ViewHistory.objects.all()

        search_qs_filtered = apply_date_range(search_qs, date_from, date_to)
        view_qs_filtered = apply_date_range(view_qs, date_from, date_to)

        searches_count = search_qs_filtered.count()
        views_count = view_qs_filtered.count()

        gap_searches_qs = search_qs_filtered.filter(results_count=0)
        gap_searches_count = gap_searches_qs.count()

        recent_gap_searches = gap_searches_qs.order_by("-created_at")[:10]
        gap_details = [
            {
                "keyword": s.keyword,
                "user": s.user.email if s.user else None,
                "created_at": s.created_at,
            }
            for s in recent_gap_searches
        ]

        # 3. TOP5
        top_viewed_listings = (
            view_qs_filtered.values("listing_id", "listing__title")
            .annotate(views_count=Count("id"))
            .order_by("-views_count")[:5]
        )

        data = {
            "period": {
                "date_from": date_from,
                "date_to": date_to,
            },
            "summary": {
                "searches_count": searches_count,
                "views_count": views_count,
            },
            "gap_analysis": {
                "total_zero_result_searches": gap_searches_count,
                "recent_zero_result_searches": gap_details,
            },
            "top_trending_listings": list(top_viewed_listings),
        }

        return Response(data, status=status.HTTP_200_OK)
