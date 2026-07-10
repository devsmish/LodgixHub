from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from core.models import TimestampedModel
from apps.listings.models import Listing, Room
from apps.bookings.choices import BookingStatus, CancellationReason, DisputeStatus
from apps.bookings.constants import (
    MAX_BOOKING_DURATION_DAYS,
    DAILY_RENTAL_MAX_DAYS,
    LONG_TERM_MIN_DAYS
)


class Booking(TimestampedModel):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="bookings"
    )
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, null=True, blank=True)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, null=True, blank=True)

    status = models.CharField(
        max_length=30,
        choices=BookingStatus,
        default=BookingStatus.PENDING
    )

    check_in_at = models.DateTimeField(verbose_name=_("Check-in time"))
    check_out_at = models.DateTimeField(verbose_name=_("Check-out time"))

    guests_count = models.PositiveIntegerField()
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    deposit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    cancellation_reason = models.CharField(
        max_length=50,
        choices=CancellationReason,
        blank=True,
        null=True
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(check_out_at__gt=models.F("check_in_at")),
                name="booking_check_out_after_check_in"
            ),
            models.CheckConstraint(
                condition=models.Q(total_price__gte=0),
                name="booking_total_price_non_negative"
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(listing__isnull=False, room__isnull=True) |
                    models.Q(listing__isnull=True, room__isnull=False)
                ),
                name="booking_xor_listing_or_room"
            )
        ]
        indexes = [
            models.Index(fields=['check_in_at', 'check_out_at']),
        ]

    def clean(self):
        super().clean()

        target = self.room if self.room else self.listing
        if not target:
            raise ValidationError({"listing": _("Please select a listing or a room.")})

        # Time validation
        if self.check_in_at.time() != target.check_in_time:
            raise ValidationError({"check_in_at": _(f"Check-in must be at {target.check_in_time}.")})
        if self.check_out_at.time() != target.check_out_time:
            raise ValidationError({"check_out_at": _(f"Check-out must be at {target.check_out_time}.")})
        if self.check_in_at >= self.check_out_at:
            raise ValidationError({"check_out_date": _("Check-out date must be after check-in.")})

        # Date validation: cannot book in the past
        if self.check_in_at < timezone.now():
            raise ValidationError({"check_in_at": _("Check-in time cannot be in the past.")})
        if self.check_in_at >= self.check_out_at:
            raise ValidationError({"check_out_at": _("Check-out must be after check-in.")})

        # RentalType validation (relationship with Listing)
        duration_days = (self.check_out_at - self.check_in_at).days
        if duration_days > MAX_BOOKING_DURATION_DAYS:
            raise ValidationError({"check_out_at": _("Booking duration cannot exceed 1 year.")})

        listing = self.listing if self.listing else self.room.listing
        if listing:
            if listing.rental_type == 'daily' and duration_days > DAILY_RENTAL_MAX_DAYS:
                raise ValidationError({"check_out_at": _(f"Daily rentals cannot exceed {DAILY_RENTAL_MAX_DAYS} days.")})
            elif listing.rental_type == 'long_term' and duration_days < LONG_TERM_MIN_DAYS:
                raise ValidationError(
                    {"check_out_at": _(f"Long-term rentals must be at least {LONG_TERM_MIN_DAYS} days.")})

        # Date Overlap Check
        qs = Booking.objects.filter(
            check_in_at__lt=self.check_out_at,
            check_out_at__gt=self.check_in_at,
        ).exclude(status__in=[
            BookingStatus.CANCELLED_BY_TENANT,
            BookingStatus.REJECTED,
            BookingStatus.AUTO_CANCELLED
        ])

        if self.listing:
            qs = qs.filter(listing=self.listing)
        else:
            qs = qs.filter(room=self.room)

        if self.pk: qs = qs.exclude(pk=self.pk)

        if qs.exists():
            raise ValidationError(_("These dates are already booked."))

        # Capacity validation
        if self.guests_count > target.max_guests:
            raise ValidationError({"guests_count": _("Number of guests exceeds capacity.")})

        # Protecting integrity in disputes
        if self.pk and self.disputes.filter(status=DisputeStatus.OPEN).exists():
            raise ValidationError(_("Cannot modify a booking with an active dispute."))

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Booking {self.id} for {self.owner}"


class Dispute(TimestampedModel):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="disputes")
    status = models.CharField(max_length=30, choices=DisputeStatus, default=DisputeStatus.OPEN)
    description = models.TextField()
    evidence_url = models.URLField(blank=True, null=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["booking", "status"])]
