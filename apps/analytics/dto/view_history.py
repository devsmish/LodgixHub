from rest_framework import serializers

from apps.analytics.models import ViewHistory


class ViewHistoryOutDTO(serializers.ModelSerializer):
    """GET /api/view-history/mine/"""

    listing_id = serializers.UUIDField(source="listing.id", read_only=True)
    listing_title = serializers.CharField(source="listing.title", read_only=True)
    listing_current_price = serializers.DecimalField(
        source="listing.current_price", read_only=True, max_digits=10, decimal_places=2
    )

    class Meta:
        model = ViewHistory
        fields = (
            "id",
            "listing_id",
            "listing_title",
            "listing_current_price",
            "created_at",
        )
        read_only_fields = fields
