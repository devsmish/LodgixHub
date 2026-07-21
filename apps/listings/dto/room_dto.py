from rest_framework import serializers

from apps.listings.models import Room


class RoomSerializer(serializers.ModelSerializer):
    """GET .../rooms/ — list of room categories. `available_count` is populated
    only when `check_in`/`check_out` are provided."""

    available_count = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = (
            "id",
            "listing",
            "room_type",
            "name",
            "max_guests",
            "rooms_available_count",
            "check_in_time",
            "check_out_time",
            "available_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "listing", "created_at", "updated_at")

    def get_available_count(self, obj):
        return getattr(obj, "_available_count", None)


class RoomCreateSerializer(serializers.ModelSerializer):
    """POST .../rooms/ — the `listing` is set in `services` from the URL;
    when `listing.type` is `'apartment'`, validation is performed in `Room.clean()`."""

    class Meta:
        model = Room
        fields = (
            "room_type",
            "name",
            "max_guests",
            "rooms_available_count",
            "check_in_time",
            "check_out_time",
        )


class RoomUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = (
            "room_type",
            "name",
            "max_guests",
            "rooms_available_count",
            "check_in_time",
            "check_out_time",
        )
