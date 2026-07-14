from rest_framework import generics, permissions

from apps.analytics.dto.view_history import ViewHistoryOutDTO
from apps.analytics.paginations import AnalyticsPagination
from apps.analytics.services import ViewHistoryService


class MyViewHistoryView(generics.ListAPIView):
    """
    GET /api/view-history/mine/
    Access: authorized user.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ViewHistoryOutDTO
    pagination_class = AnalyticsPagination

    def get_queryset(self):
        return ViewHistoryService().get_my_history(self.request.user)
