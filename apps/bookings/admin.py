from django.contrib import admin

from .choices import DisputeStatus
from .models import Booking, Dispute


class DisputeInline(admin.TabularInline):
    model = Dispute
    extra = 0
    readonly_fields = ('created_at',)

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "owner_email",
        "status",
        "check_in_at",
        "check_out_at",
        "total_price",
        "has_active_dispute"
    )
    list_filter = ("status", "check_in_at")
    search_fields = ("owner__email", "id", "listing__name", "room__name")
    readonly_fields = ("created_at", "updated_at")
    inlines = [DisputeInline]
    date_hierarchy = 'check_in_at'

    def owner_email(self, obj):
        return obj.owner.email
    owner_email.short_description = "Owner Email"

    def has_active_dispute(self, obj):
        return obj.disputes.filter(status=DisputeStatus.OPEN).exists()
    has_active_dispute.boolean = True
    has_active_dispute.short_description = "Active Dispute"

@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):
    list_display = ("id", "booking_id", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("booking__id", "description")
    readonly_fields = ("created_at",)
