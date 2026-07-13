from django.contrib import admin

from apps.analytics.models import SearchHistory, ViewHistory


class ReadOnlyLogAdminMixin:
    """LogModel — append-only: creation and editing via the admin panel are disabled."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(SearchHistory)
class SearchHistoryAdmin(ReadOnlyLogAdminMixin, admin.ModelAdmin):
    list_display = ("keyword", "user", "results_count", "created_at")
    list_filter = ("created_at",)
    search_fields = ("keyword", "user__email")
    readonly_fields = ("id", "user", "keyword", "results_count", "created_at")


@admin.register(ViewHistory)
class ViewHistoryAdmin(ReadOnlyLogAdminMixin, admin.ModelAdmin):
    list_display = ("listing", "user", "session_key", "created_at")
    list_filter = ("created_at",)
    search_fields = ("listing__title", "user__email", "session_key")
    readonly_fields = ("id", "listing", "user", "session_key", "created_at")
