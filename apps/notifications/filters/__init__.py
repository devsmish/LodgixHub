class NotificationLogFilter:
    """Constructing a queryset for GET /api/v1/notifications/logs/ ."""

    def __init__(self, query_params):
        self.query_params = query_params

    def apply(self, queryset):
        user_id = self.query_params.get("user")
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        notification_type = self.query_params.get("notification_type")
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)

        success = self.query_params.get("success")
        if success is not None:
            queryset = queryset.filter(success=success.lower() in ("true", "1"))

        return queryset
