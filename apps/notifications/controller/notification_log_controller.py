from rest_framework import generics

from apps.notifications.dto import NotificationLogSerializer
from apps.notifications.filters import NotificationLogFilter
from apps.notifications.repositories import NotificationLogRepository
from apps.security.permissions import IsAdmin


class NotificationLogListView(generics.ListAPIView):
    """GET /api/v1/notifications/logs/ — Admin, with filters
    user/notification_type/success."""

    serializer_class = NotificationLogSerializer
    permission_classes = [IsAdmin]

    repository = NotificationLogRepository()

    def get_queryset(self):
        queryset = self.repository.get_all_queryset()
        return NotificationLogFilter(self.request.query_params).apply(queryset)
