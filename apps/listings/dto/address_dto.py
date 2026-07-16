from rest_framework import serializers

from apps.listings.models import Address


class AddressSerializer(serializers.ModelSerializer):

    class Meta:
        model = Address
        fields = (
            "country",
            "region",
            "city",
            "district",
            "street",
            "house_number",
            "postal_code",
            "floor",
            "apartment_number",
            "latitude",
            "longitude",
        )
