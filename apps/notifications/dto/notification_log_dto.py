from rest_framework import serializers

from apps.notifications.models import NotificationLog


class NotificationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationLog
        fields = (
            "id",
            "user",
            "notification_type",
            "success",
            "error_message",
            "created_at",
        )
        read_only_fields = fields
