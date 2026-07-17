from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.bookings.choices import BookingStatus
from apps.bookings.models.cancellation_reason import CancellationReason
from apps.bookings.validators.booking_validators import (
    validate_active_disputes_on_write,
    validate_booking_capacity,
    validate_booking_dates_basic,
    validate_booking_duration,
    validate_booking_overlap,
    validate_booking_target,
)
from core.models import TimestampedModel


class Booking(TimestampedModel):
    tenant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="bookings",
        verbose_name=_("Tenant"),
    )

    # lazy strings to avoid circular imports
    listing = models.ForeignKey(
        "listings.Listing", on_delete=models.CASCADE, null=True, blank=True
    )
    room = models.ForeignKey(
        "listings.Room", on_delete=models.CASCADE, null=True, blank=True
    )

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

        validate_booking_target(self.listing, self.room)
        validate_booking_dates_basic(self.check_in_date, self.check_out_date)

        validate_booking_duration(self)
        validate_booking_capacity(self)
        validate_active_disputes_on_write(self)

        validate_booking_overlap(self, Booking)

    def get_landlord(self):
        listing = self.listing or (self.room.listing if self.room else None)
        return listing.owner if listing else None

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Booking {self.id} for {self.tenant}"
