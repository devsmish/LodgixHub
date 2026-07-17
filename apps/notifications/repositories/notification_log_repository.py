from apps.notifications.models import NotificationLog


class NotificationLogRepository:

    @staticmethod
    def get_all_queryset():
        return NotificationLog.objects.select_related("user").order_by("-created_at")
