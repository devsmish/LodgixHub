from rest_framework import serializers

from apps.bookings.models import Booking


class BookingCreateSerializer(serializers.Serializer):
    """POST /api/v1/bookings/ — ровно одно из listing_id/room_id (ТЗ 2.8)."""

    listing_id = serializers.UUIDField(required=False)
    room_id = serializers.UUIDField(required=False)
    check_in_date = serializers.DateField()
    check_out_date = serializers.DateField()
    guests_count = serializers.IntegerField(min_value=1)

    def validate(self, attrs):
        listing_id = attrs.get("listing_id")
        room_id = attrs.get("room_id")
        if bool(listing_id) == bool(room_id):
            raise serializers.ValidationError(
                "Укажите либо listing_id, либо room_id (ровно одно)."
            )
        if attrs["check_in_date"] >= attrs["check_out_date"]:
            raise serializers.ValidationError(
                {"check_out_date": "Дата выезда должна быть позже даты заезда."}
            )
        return attrs


class BookingSerializer(serializers.ModelSerializer):
    """GET /api/v1/bookings/ и /{id}/ — read-only, total_price всегда фиксирован
    на момент создания (ТЗ 2.5) и не редактируется ни этим, ни другим сериализатором."""

    class Meta:
        model = Booking
        fields = (
            "id",
            "tenant",
            "listing",
            "room",
            "status",
            "check_in_date",
            "check_out_date",
            "guests_count",
            "total_price",
            "deposit_amount",
            "deposit_refunded",
            "cancellation_reason",
            "cancelled_by",
            "confirmed_at",
            "cancelled_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class BookingCancelSerializer(serializers.Serializer):
    """POST /api/v1/bookings/{id}/cancel/ — cancellation_reason_id обязателен
    только когда отменяет владелец (проверяется в services, не здесь, так как
    зависит от того, кто именно — арендатор или владелец — делает запрос)."""

    cancellation_reason_id = serializers.UUIDField(required=False)
