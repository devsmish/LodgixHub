from django.contrib import admin

from apps.pricing.models import PriceHistory


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ("listing", "room", "price", "currency", "effective_date")
    list_filter = ("effective_date", "currency")
    readonly_fields = (
        "listing",
        "room",
        "price",
        "currency",
        "effective_date",
    )  # Disabling edits in the admin panel

    def has_change_permission(self, request, obj=None):
        return False  # Prohibition on editing history records

    def has_delete_permission(self, request, obj=None):
        return False  # Deletion prohibition
