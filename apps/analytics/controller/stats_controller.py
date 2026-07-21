from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.services import AdminDashboardStatsService
from apps.security.permissions import IsAdmin
from apps.analytics.constants import ADMIN_DASHBOARD_RESPONSE_SCHEMA


class AdminDashboardStatsView(APIView):
    """
    GET /api/analytics/admin/stats/
    Returns aggregated analytics for the admin panel.
    Supports date filtering via query parameters `?date_from=...` and `?date_to=...`.
    Access: administrators only.
    """

    permission_classes = [IsAdmin]
    service = AdminDashboardStatsService()

    @extend_schema(
        parameters=[
            OpenApiParameter("date_from", str, description="ISO 8601, включительно"),
            OpenApiParameter("date_to", str, description="ISO 8601, включительно"),
        ],
        responses={200: OpenApiResponse(response=ADMIN_DASHBOARD_RESPONSE_SCHEMA)},
    )
    def get(self, request):
        data = self.service.get_summary(
            date_from=request.query_params.get("date_from"),
            date_to=request.query_params.get("date_to"),
        )
        return Response(data, status=status.HTTP_200_OK)
