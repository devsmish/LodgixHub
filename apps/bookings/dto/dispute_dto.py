from decimal import Decimal

from rest_framework import serializers

from apps.bookings.choices import (
    DisputeReason,
    DisputeResolutionFavor,
    DisputeStatus,
)
from apps.bookings.models import Dispute, DisputeEvidence


class DisputeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dispute
        fields = (
            "id",
            "booking",
            "opened_by",
            "reason_category",
            "reason",
            "status",
            "claim_amount",
            "resolved_at",
            "resolved_by",
            "resolution_amount",
            "resolution_favor",
            "moderator_notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class DisputeCreateSerializer(serializers.Serializer):
    reason_category = serializers.ChoiceField(choices=DisputeReason.choices)
    reason = serializers.CharField()
    claim_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, default=Decimal("0.00")
    )


class DisputeResolveSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=(
            (DisputeStatus.RESOLVED_REFUNDED, DisputeStatus.RESOLVED_REFUNDED.label),
            (DisputeStatus.RESOLVED_REJECTED, DisputeStatus.RESOLVED_REJECTED.label),
        )
    )
    resolution_favor = serializers.ChoiceField(choices=DisputeResolutionFavor.choices)
    resolution_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class DisputeEvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DisputeEvidence
        fields = ("id", "dispute", "uploaded_by", "url", "description", "created_at")
        read_only_fields = fields


class DisputeEvidenceCreateSerializer(serializers.Serializer):
    url = serializers.URLField()
    description = serializers.CharField(required=False, allow_blank=True, default="")
