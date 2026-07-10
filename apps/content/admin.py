from django.contrib import admin

from apps.content.models import Photo


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ("id", "listing", "room", "created_at")
    list_filter = ("listing", "room")
    search_fields = ("listing__id", "room__id")
