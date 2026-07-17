from rest_framework import serializers

from apps.content.models import Photo


class PhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Photo
        fields = (
            "id",
            "listing",
            "room",
            "image",
            "caption",
            "is_primary",
            "order",
            "uploaded_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "listing",
            "room",
            "uploaded_by",
            "created_at",
            "updated_at",
        )


class PhotoCreateSerializer(serializers.ModelSerializer):
    """POST .../photos/ — listing/uploaded_by are set in services from the URL/request."""

    class Meta:
        model = Photo
        fields = ("image", "caption", "is_primary", "order")


class PhotoUpdateSerializer(serializers.ModelSerializer):
    """PATCH .../photos/{id}/ — only order/caption/is_primary."""

    class Meta:
        model = Photo
        fields = ("caption", "is_primary", "order")
