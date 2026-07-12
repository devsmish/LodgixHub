from django.contrib import admin

from apps.bookings.choices import DisputeStatus
from apps.bookings.models import Booking, CancellationReason, Dispute


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


@admin.register(CancellationReason)
class CancellationReasonAdmin(admin.ModelAdmin):
    list_display = ("code", "description")
    search_fields = ("code", "description")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tenant_email",
        "status",
        "check_in_date",
        "check_out_date",
        "total_price",
        "deposit_refunded",
        "has_active_dispute",
    )
    list_filter = ("status", "check_in_date")
    search_fields = ("tenant__email", "id", "listing__title", "room__name")
    raw_id_fields = ("tenant", "cancelled_by", "cancellation_reason", "listing", "room")
    readonly_fields = ("created_at", "updated_at", "confirmed_at", "cancelled_at")
    inlines = [DisputeInline]
    date_hierarchy = "check_in_date"

    def tenant_email(self, obj):
        return obj.tenant.email

    tenant_email.short_description = "Tenant"

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
