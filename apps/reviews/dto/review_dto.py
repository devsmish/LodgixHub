from rest_framework import serializers

from apps.reviews.choices import ReviewStatus
from apps.reviews.models import Review


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = (
            "id",
            "booking",
            "listing",
            "author",
            "rating",
            "comment",
            "status",
            "landlord_response",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ReviewCreateSerializer(serializers.Serializer):
    """POST /api/v1/reviews/ — for a specific booking."""

    booking_id = serializers.UUIDField()
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(required=False, allow_blank=True, default="")


class ReviewUpdateSerializer(serializers.Serializer):
    """PATCH /api/v1/reviews/{id}/ — author only, and only within the 7-day window
    (the window is checked in Review.clean(), not here)."""

    rating = serializers.IntegerField(min_value=1, max_value=5, required=False)
    comment = serializers.CharField(required=False, allow_blank=True)


class ReviewRespondSerializer(serializers.Serializer):
    landlord_response = serializers.CharField(max_length=1000)


class ReviewStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ReviewStatus.choices)
