from rest_framework import serializers

from apps.bookings.models import CancellationReason


class CancellationReasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = CancellationReason
        fields = ("id", "code", "description")
        read_only_fields = ("id",)
