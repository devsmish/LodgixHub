from django.contrib import admin

from apps.listings.models import Amenity, Listing


@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "group", "icon")
    list_filter = ("group",)
    search_fields = ("name", "slug")
    readonly_fields = ("group",)


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ("title",)
    filter_horizontal = ("amenities",)
