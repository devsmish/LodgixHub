from django.contrib import admin

from apps.notifications.models import NotificationLog


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ("notification_type", "user", "success", "created_at")
    list_filter = ("notification_type", "success")
    search_fields = ("user__email", "error_message")
    raw_id_fields = ("user",)
    readonly_fields = (
        "user",
        "notification_type",
        "success",
        "error_message",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
