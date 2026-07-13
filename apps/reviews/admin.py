from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "listing",
        "author",
        "rating",
        "status",
        "has_landlord_response",
        "created_at",
    )
    list_filter = ("status", "rating")
    search_fields = ("listing__title", "author__email", "comment")
    raw_id_fields = ("booking", "listing", "author")
    readonly_fields = ("created_at", "updated_at")

    def has_landlord_response(self, obj):
        return bool(obj.landlord_response)

    has_landlord_response.boolean = True
    has_landlord_response.short_description = "Landlord Responded"
