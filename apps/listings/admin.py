from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.listings.models import Amenity, Listing, Room


class RoomInline(admin.TabularInline):
    model = Room
    extra = 1
    fields = ("room_type", "name", "max_guests")


@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "group", "icon")
    list_filter = ("group",)
    search_fields = ("name", "slug")
    readonly_fields = ("group",)


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "type",
        "status",
        "owner",
        "price_per_night",
        "max_guests",
        "created_at",
    )

    list_filter = ("type", "status", "rental_type", "meal_type", "created_at")

    search_fields = ("title", "owner__username", "owner__email")

    filter_horizontal = ("amenities",)

    inlines = [RoomInline]

    fieldsets = (
        (None, {"fields": ("title", "description", "owner", "status", "type")}),
        (_("Location & Capacity"), {"fields": ("latitude", "longitude", "max_guests")}),
        (
            _("Pricing & Rules"),
            {"fields": ("price_per_night", "rental_type", "meal_type")},
        ),
        (_("Amenities & Features"), {"fields": ("amenities",)}),
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
