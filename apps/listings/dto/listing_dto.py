from rest_framework import serializers

from apps.listings.choices import ListingStatus
from apps.listings.dto.address_dto import AddressSerializer
from apps.listings.dto.amenity_dto import AmenitySerializer
from apps.listings.models import Amenity, Listing


class ListingListSerializer(serializers.ModelSerializer):
    """GET /api/v1/listings/ — lightweight representation for the list."""

    city = serializers.CharField(source="address.city", read_only=True)
    district = serializers.CharField(source="address.district", read_only=True)

    class Meta:
        model = Listing
        fields = (
            "id",
            "title",
            "type",
            "status",
            "is_active",
            "current_price",
            "rental_type",
            "max_guests",
            "rooms_count",
            "views_count",
            "rating_avg",
            "reviews_count",
            "city",
            "district",
            "created_at",
        )
        read_only_fields = fields


class ListingDetailSerializer(serializers.ModelSerializer):
    """GET /api/v1/listings/{id}/ — full view."""

    address = AddressSerializer(read_only=True)
    amenities = AmenitySerializer(many=True, read_only=True)

    class Meta:
        model = Listing
        fields = (
            "id",
            "owner",
            "title",
            "description",
            "type",
            "status",
            "is_active",
            "address",
            "max_guests",
            "rooms_count",
            "current_price",
            "rental_type",
            "meal_type",
            "deposit_required",
            "deposit_percent",
            "deposit_refundable",
            "views_count",
            "rating_avg",
            "reviews_count",
            "amenities",
            "check_in_time",
            "check_out_time",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "owner",
            "views_count",
            "rating_avg",
            "reviews_count",
            "current_price",
            "created_at",
            "updated_at",
        )


class ListingCreateSerializer(serializers.ModelSerializer):
    """POST /api/v1/listings/ — owner and status=draft are set in the services;
    they are not accepted from the client."""

    address = AddressSerializer()

    class Meta:
        model = Listing
        fields = (
            "title",
            "description",
            "type",
            "address",
            "max_guests",
            "rooms_count",
            "current_price",
            "rental_type",
            "meal_type",
            "deposit_required",
            "deposit_percent",
            "deposit_refundable",
            "check_in_time",
            "check_out_time",
        )


class ListingUpdateSerializer(serializers.ModelSerializer):
    """PATCH /api/v1/listings/{id}/ — 'type' following is intentionally excluded:
    immutability is checked in services against the raw `request.data`."""

    address = AddressSerializer(required=False)

    class Meta:
        model = Listing
        fields = (
            "title",
            "description",
            "address",
            "max_guests",
            "rooms_count",
            "rental_type",
            "meal_type",
            "deposit_required",
            "deposit_percent",
            "deposit_refundable",
            "check_in_time",
            "check_out_time",
        )


class ListingStatusUpdateSerializer(serializers.Serializer):
    """PATCH /api/v1/listings/{id}/status/ — a separate, narrow status transition."""

    status = serializers.ChoiceField(choices=ListingStatus.choices)


class ListingAmenitiesUpdateSerializer(serializers.Serializer):
    """PUT /api/v1/listings/{id}/amenities/ — complete replacement of the set of amenities.
    Accepts a list of amenity_ids.."""

    amenity_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Amenity.objects.all()
    )
