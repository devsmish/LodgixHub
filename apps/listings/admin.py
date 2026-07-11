from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.listings.models import Address, Amenity, Listing, ListingAmenity, Room


class RoomInline(admin.TabularInline):
    model = Room
    extra = 1
    fields = ("room_type", "name", "max_guests")


class ListingAmenityInline(admin.TabularInline):
    model = ListingAmenity
    extra = 1


@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "group", "icon")
    list_filter = ("group",)
    search_fields = ("name", "slug")
    readonly_fields = ("group",)


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("city", "street", "house_number", "postal_code", "region")
    list_filter = ("country", "region", "city")
    search_fields = ("city", "street", "postal_code")


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "type",
        "status",
        "is_active",
        "owner",
        "current_price",
        "max_guests",
        "views_count",
        "created_at",
    )

    list_filter = (
        "type",
        "status",
        "is_active",
        "rental_type",
        "meal_type",
        "created_at",
    )

    search_fields = ("title", "owner__email", "owner__nickname")

    inlines = [RoomInline, ListingAmenityInline]

    readonly_fields = ("views_count", "rating_avg", "reviews_count")

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "title",
                    "description",
                    "owner",
                    "status",
                    "type",
                    "is_active",
                )
            },
        ),
        (
            _("Location & Capacity"),
            {"fields": ("address", "max_guests", "rooms_count")},
        ),
        (
            _("Pricing & Rules"),
            {"fields": ("current_price", "rental_type", "meal_type")},
        ),
        (
            _("Deposit"),
            {"fields": ("deposit_required", "deposit_percent", "deposit_refundable")},
        ),
        (
            _("Analytics"),
            {"fields": ("views_count", "rating_avg", "reviews_count")},
        ),
    )


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "room_type",
        "name",
        "listing",
        "max_guests",
        "created_at",
        "deleted_at",
    )
    list_filter = ("room_type", "listing__type")
    search_fields = ("name", "listing__title")

    def get_queryset(self, request):
        return Room.all_objects.get_queryset()
