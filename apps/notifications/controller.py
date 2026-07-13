from rest_framework import generics

from apps.notifications.models import NotificationLog
from apps.security.permissions import IsAdmin


class NotificationLogListView(generics.ListAPIView):

    queryset = NotificationLog.objects.all()
    permission_classes = [IsAdmin]
