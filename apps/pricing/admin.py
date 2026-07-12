from django.contrib import admin

from apps.pricing.models import PriceHistory


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "listing",
        "room",
        "price",
        "currency",
        "valid_from",
        "changed_by",
        "created_at",
    )
    list_filter = ("valid_from", "currency")
    raw_id_fields = ("listing", "room", "changed_by")
    readonly_fields = (
        "listing",
        "room",
        "price",
        "currency",
        "valid_from",
        "changed_by",
        "created_at",
    )  # Disabling edits in the admin panel

    def has_add_permission(self, request):
        """
        This function prevents manual price setting in the admin panel.
        If a manual override is required for support staff, this function
        should be removed and `changed_by = request.user` should be
        set in `save_model()`.
        """
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
