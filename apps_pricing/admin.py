from django.contrib import admin

from apps.pricing.models import PriceHistory


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "listing",
        "room",
        "price",
        "currency",
        "valid_from",  # CHANGED: было effective_date
        "changed_by",  # NEW
        "created_at",
    )
    list_filter = ("valid_from", "currency")  # CHANGED: было effective_date
    raw_id_fields = ("listing", "room", "changed_by")  # NEW
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
        # CHANGED: раньше add был формально разрешён, но все поля readonly —
        # форма создания была бы пустой и нерабочей. Модель append-only,
        # цены должны идти только через POST /api/listings/{id}/price/
        # (раздел 2.12 ТЗ) или через cron — не через ручной ввод в админке.
        # Если нужен ручной override для саппорта, эту функцию нужно убрать
        # и подставлять changed_by = request.user в save_model().
        return False

    def has_change_permission(self, request, obj=None):
        return False  # Prohibition on editing history records

    def has_delete_permission(self, request, obj=None):
        return False  # Deletion prohibition
