from django.contrib import admin

from .choices import DisputeStatus
from .models import Booking, Dispute


class DisputeInline(admin.StackedInline):
    model = Dispute
    extra = 0
    readonly_fields = ("created_at", "resolved_at")
    fields = (
        "status",
        "reason_category",
        "reason",
        "claim_amount",
        "evidence_url",
        "resolved_at",
        "created_at",
    )


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "owner_email",
        "status",
        "check_in_at",
        "check_out_at",
        "total_price",
        "has_active_dispute",
    )
    list_filter = ("status", "check_in_at")
    search_fields = ("owner__email", "id", "listing__name", "room__name")
    readonly_fields = ("created_at", "updated_at")
    inlines = [DisputeInline]
    date_hierarchy = "check_in_at"

    def owner_email(self, obj):
        return obj.owner.email

    def has_active_dispute(self, obj):
        return hasattr(obj, "dispute") and obj.dispute.status == DisputeStatus.OPEN

    has_active_dispute.boolean = True
    has_active_dispute.short_description = "Active Dispute"


@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "booking",
        "status",
        "reason_category",
        "claim_amount",
        "created_at",
    )
    list_filter = ("status", "reason_category")
    search_fields = ("booking__id", "reason")
    readonly_fields = ("created_at", "updated_at", "resolved_at")
    raw_id_fields = ("booking",)
