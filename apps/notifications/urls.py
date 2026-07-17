from django.urls import path

from apps.notifications.controller import NotificationLogListView

app_name = "notifications"

urlpatterns = [
    path(
        "notifications/logs/",
        NotificationLogListView.as_view(),
        name="notification-logs",
    ),
]
