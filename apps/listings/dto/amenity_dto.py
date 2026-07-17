from rest_framework import serializers

from apps.listings.models import Amenity


class AmenitySerializer(serializers.ModelSerializer):
    """GET/POST /api/v1/amenities/ ."""

    class Meta:
        model = Amenity
        fields = ("id", "name", "slug", "group", "icon")
        read_only_fields = ("id", "group")


class AmenityUpdateSerializer(serializers.ModelSerializer):
    """PATCH /api/v1/amenities/{id}/ — editing name/icon;
    slug — a system key; it cannot be changed after creation."""

    class Meta:
        model = Amenity
        fields = ("name", "icon")
