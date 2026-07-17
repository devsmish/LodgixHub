from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.bookings.choices import (
    DisputeReason,
    DisputeResolutionFavor,
    DisputeStatus,
)
from apps.bookings.models.booking import Booking
from apps.bookings.validators.dispute_validators import (
    validate_dispute_amounts,
    validate_dispute_booking_status,
    validate_dispute_opener,
    validate_dispute_resolution,
    validate_dispute_status_transitions,
    validate_dispute_timeline,
    validate_duplicate_disputes,
    validate_evidence_uploader,
)
from core.models import BaseModel, TimestampedModel


class Dispute(TimestampedModel):
    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, related_name="disputes"
    )
    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="opened_disputes",
    )
    reason_category = models.CharField(
        max_length=50, choices=DisputeReason, default=DisputeReason.OTHER
    )
    reason = models.TextField(help_text="Detailed description of the issue")
    status = models.CharField(
        max_length=30, choices=DisputeStatus, default=DisputeStatus.OPEN
    )
    claim_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name=_("Claim amount")
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_disputes",
        verbose_name=_("Resolved by"),
    )
    resolution_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Resolution amount"),
        help_text=_("The amount actually awarded may be less than the claim_amount."),
    )
    resolution_favor = models.CharField(
        max_length=20,
        choices=DisputeResolutionFavor,
        null=True,
        blank=True,
        verbose_name=_("Resolution favors"),
    )
    moderator_notes = models.TextField(blank=True, verbose_name=_("Moderator notes"))

    class Meta:
        indexes = [models.Index(fields=["booking", "status"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(claim_amount__gte=0),
                name="dispute_claim_amount_non_negative",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(status=DisputeStatus.OPEN)
                    | models.Q(status=DisputeStatus.UNDER_REVIEW)
                    | (
                        models.Q(
                            status__in=[
                                DisputeStatus.RESOLVED_REFUNDED,
                                DisputeStatus.RESOLVED_REJECTED,
                            ]
                        )
                        & models.Q(resolved_at__isnull=False)
                    )
                ),
                name="dispute_resolution_date_required",
            ),
        ]

    def clean(self):
        super().clean()

        # Validation of participants and status
        validate_dispute_opener(self)
        validate_dispute_booking_status(self.booking)

        # Validation of the timeline and duplication constraints
        validate_dispute_timeline(self)
        validate_duplicate_disputes(self, Dispute)

        # Monetary checks and FSM transitions
        validate_dispute_status_transitions(self, Dispute)
        validate_dispute_amounts(self)

        # Checks of closure stages by the moderator
        validate_dispute_resolution(self)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Dispute {self.id} on booking {self.booking_id}"


class DisputeEvidence(BaseModel):
    dispute = models.ForeignKey(
        Dispute, on_delete=models.CASCADE, related_name="evidence"
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dispute_evidence",
    )
    url = models.URLField(verbose_name=_("Evidence URL"))
    description = models.CharField(
        max_length=255, blank=True, verbose_name=_("Description")
    )

    class Meta:
        verbose_name = _("Dispute Evidence")
        verbose_name_plural = _("Dispute Evidence")

    def clean(self):
        super().clean()
        validate_evidence_uploader(self)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.url
