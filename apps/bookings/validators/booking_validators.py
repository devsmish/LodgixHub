from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.bookings.choices import BookingStatus, DisputeStatus
from apps.bookings.constants import (
    DAILY_RENTAL_MAX_DAYS,
    LONG_TERM_MIN_DAYS,
    MAX_BOOKING_DURATION_DAYS,
)
from apps.listings.choices import RentalType


def validate_booking_target(listing, room):
    """Verifies that only one item is selected: an ad or a room."""
    if bool(listing) == bool(room):
        raise ValidationError(
            _("Please select either a listing or a room (exactly one).")
        )


def validate_booking_dates_basic(check_in_date, check_out_date):
    """Basic validation of dates for logical consistency and past tense."""
    if check_in_date >= check_out_date:
        raise ValidationError(
            {"check_out_date": _("Check-out date must be after check-in.")}
        )

    if check_in_date < timezone.now().date():
        raise ValidationError(
            {"check_in_date": _("Check-in date cannot be in the past.")}
        )


def validate_booking_duration(booking):
    """Duration check based on rental type."""
    duration_days = (booking.check_out_date - booking.check_in_date).days

    if duration_days > MAX_BOOKING_DURATION_DAYS:
        raise ValidationError(
            {"check_out_date": _("Booking duration cannot exceed 1 year.")}
        )

    listing = booking.listing if booking.listing else booking.room.listing
    if not listing:
        return

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


def validate_booking_capacity(booking):
    """Checking guest capacity."""
    target = booking.room if booking.room else booking.listing
    if target and booking.guests_count > target.max_guests:
        raise ValidationError({"guests_count": _("Number of guests exceeds capacity.")})


def validate_active_disputes_on_write(booking):
    """Prohibition on modifying the booking while an active dispute exists."""
    if booking._state.adding:
        return

    has_active_disputes = booking.disputes.filter(
        status__in=[DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW]
    ).exists()

    if has_active_disputes:
        raise ValidationError(_("Cannot modify a booking with an active dispute."))


def validate_booking_overlap(booking, booking_model):
    """Date overlap check for apartments and hotels."""
    qs = booking_model.objects.filter(
        check_in_date__lt=booking.check_out_date,
        check_out_date__gt=booking.check_in_date,
    ).exclude(
        status__in=[
            BookingStatus.CANCELLED_BY_TENANT,
            BookingStatus.CANCELLED_BY_LANDLORD,
            BookingStatus.REJECTED,
            BookingStatus.AUTO_CANCELLED,
        ]
    )

    if not booking._state.adding:
        qs = qs.exclude(pk=booking.pk)

    if booking.listing:
        if qs.filter(listing=booking.listing).exists():
            raise ValidationError(_("These dates are already booked."))
    elif booking.room:
        overlapping_count = qs.filter(room=booking.room).count()
        if overlapping_count >= booking.room.rooms_available_count:
            raise ValidationError(_("These dates are already booked."))
