from django.contrib import admin

from apps.content.models import Photo


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "listing",
        "room",
        "is_primary",
        "order",
        "uploaded_by",
        "created_at",
    )
    list_filter = ("listing", "room", "is_primary")
    search_fields = ("listing__title", "room__name", "caption")
    raw_id_fields = ("listing", "room", "uploaded_by")
