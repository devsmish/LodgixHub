from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.bookings.choices import (
    BookingStatus,
    DisputeReason,
    DisputeStatus,
    StandardCancellationReason,
)
from apps.bookings.constants import (
    DAILY_RENTAL_MAX_DAYS,
    DISPUTE_OPEN_WINDOW_DAYS,
    LONG_TERM_MIN_DAYS,
    MAX_BOOKING_DURATION_DAYS,
)
from apps.listings.choices import RentalType
from apps.listings.models import Listing, Room
from core.models import BaseModel, TimestampedModel


class CancellationReason(BaseModel):

    code = models.CharField(
        max_length=50,
        unique=True,
        choices=StandardCancellationReason,
        verbose_name=_("Code"),
    )
    description = models.CharField(max_length=255, verbose_name=_("Description"))

    class Meta:
        verbose_name = _("Cancellation Reason")
        verbose_name_plural = _("Cancellation Reasons")

    def __str__(self):
        return self.description


class Booking(TimestampedModel):
    tenant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="bookings",
        verbose_name=_("Tenant"),
    )

    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, null=True, blank=True
    )
    room = models.ForeignKey(Room, on_delete=models.CASCADE, null=True, blank=True)

    status = models.CharField(
        max_length=30, choices=BookingStatus, default=BookingStatus.PENDING
    )

    check_in_date = models.DateField(verbose_name=_("Check-in date"))
    check_out_date = models.DateField(verbose_name=_("Check-out date"))

    guests_count = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name=_("Guests count"),
    )
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    deposit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deposit_refunded = models.BooleanField(
        default=False, verbose_name=_("Deposit refunded")
    )

    cancellation_reason = models.ForeignKey(
        CancellationReason,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="bookings",
        verbose_name=_("Cancellation reason"),
    )

    confirmed_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Confirmed at")
    )
    cancelled_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Cancelled at")
    )
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cancelled_bookings",
        verbose_name=_("Cancelled by"),
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(check_out_date__gt=models.F("check_in_date")),
                name="booking_check_out_after_check_in",
            ),
            models.CheckConstraint(
                condition=models.Q(total_price__gte=0),
                name="booking_total_price_non_negative",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(listing__isnull=False, room__isnull=True)
                    | models.Q(listing__isnull=True, room__isnull=False)
                ),
                name="booking_xor_listing_or_room",
            ),
        ]
        indexes = [
            models.Index(fields=["check_in_date", "check_out_date"]),
        ]

    def clean(self):
        super().clean()

        target = self.room if self.room else self.listing
        if not target:
            raise ValidationError({"listing": _("Please select a listing or a room.")})

        # Date validation: cannot book in the past
        if self.check_in_date >= self.check_out_date:
            raise ValidationError(
                {"check_out_date": _("Check-out date must be after check-in.")}
            )

        if self.check_in_date < timezone.now().date():
            raise ValidationError(
                {"check_in_date": _("Check-in date cannot be in the past.")}
            )

        # RentalType validation (relationship with Listing)
        duration_days = (self.check_out_date - self.check_in_date).days
        if duration_days > MAX_BOOKING_DURATION_DAYS:
            raise ValidationError(
                {"check_out_date": _("Booking duration cannot exceed 1 year.")}
            )

        listing = self.listing if self.listing else self.room.listing
        if listing:
            if (
                listing.rental_type == RentalType.DAILY
                and duration_days > DAILY_RENTAL_MAX_DAYS
            ):
                raise ValidationError(
                    {
                        "check_out_date": _(
                            f"Daily rentals cannot exceed {DAILY_RENTAL_MAX_DAYS} days."
                        )
                    }
                )
            elif (
                listing.rental_type == RentalType.LONG_TERM
                and duration_days < LONG_TERM_MIN_DAYS
            ):
                raise ValidationError(
                    {
                        "check_out_date": _(
                            f"Long-term rentals must be at least {LONG_TERM_MIN_DAYS} days."
                        )
                    }
                )

        # Date Overlap Check
        qs = Booking.objects.filter(
            check_in_date__lt=self.check_out_date,
            check_out_date__gt=self.check_in_date,
        ).exclude(
            status__in=[
                BookingStatus.CANCELLED_BY_TENANT,
                BookingStatus.CANCELLED_BY_LANDLORD,
                BookingStatus.REJECTED,
                BookingStatus.AUTO_CANCELLED,
            ]
        )

        if self.listing:
            qs = qs.filter(listing=self.listing)
        else:
            qs = qs.filter(room=self.room)

        if self.pk:
            qs = qs.exclude(pk=self.pk)

        if qs.exists():
            raise ValidationError(_("These dates are already booked."))

        # Capacity validation
        if self.guests_count > target.max_guests:
            raise ValidationError(
                {"guests_count": _("Number of guests exceeds capacity.")}
            )

        # Protecting integrity in disputes
        if (
            self.pk
            and hasattr(self, "dispute")
            and self.dispute.status == DisputeStatus.OPEN
        ):
            raise ValidationError(_("Cannot modify a booking with an active dispute."))

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Booking {self.id} for {self.tenant}"


class Dispute(TimestampedModel):
    booking = models.OneToOneField(
        Booking, on_delete=models.CASCADE, related_name="dispute"
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
    claim_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    evidence_url = models.URLField(blank=True, null=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

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

        if self.booking.status == BookingStatus.COMPLETED:
            deadline = self.booking.check_out_date + timedelta(
                days=DISPUTE_OPEN_WINDOW_DAYS
            )
            if timezone.now().date() > deadline:
                raise ValidationError(
                    _(
                        "Disputes can be opened within 3 days after the booking is completed."
                    )
                )

        if self.claim_amount < 0:
            raise ValidationError(
                {"claim_amount": _("Claim amount cannot be negative.")}
            )

        if self.claim_amount > self.booking.total_price:
            raise ValidationError(
                {"claim_amount": _("Claim amount cannot exceed total booking price.")}
            )

        if (
            self.status
            in [DisputeStatus.RESOLVED_REFUNDED, DisputeStatus.RESOLVED_REJECTED]
            and not self.resolved_at
        ):
            raise ValidationError(
                {"resolved_at": _("Resolution date is required for resolved disputes.")}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
