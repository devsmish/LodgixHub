from decimal import Decimal

from rest_framework import serializers

from apps.pricing.models import PriceHistory


class PriceHistorySerializer(serializers.ModelSerializer):
    """GET .../price-history/ — append-only log, readonly."""

    class Meta:
        model = PriceHistory
        fields = (
            "id",
            "listing",
            "room",
            "price",
            "currency",
            "valid_from",
            "changed_by",
            "created_at",
        )
        read_only_fields = fields


class PriceHistoryCreateSerializer(serializers.Serializer):
    """POST /api/v1/listings/{listing_id}/price/ — set a new price.
    Business validation (XOR listing/room, date not in the past, no "same-day"
    bookings except for the initial price)"""

    price = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0.01")
    )
    valid_from = serializers.DateField()
    currency = serializers.CharField(max_length=3, required=False, default="EUR")
