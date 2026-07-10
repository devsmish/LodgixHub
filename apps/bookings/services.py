from datetime import timedelta
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.bookings.models import Booking
from apps.bookings.choices import BookingStatus, DisputeStatus
from apps.bookings.constants import TIME_TO_CANCELLING_HOURS


def _check_dispute_status(booking: Booking):
    """Internal utility for checking open disputes."""
    if booking.disputes.filter(status=DisputeStatus.OPEN).exists():
        raise ValidationError(_("The booking cannot be modified while a dispute is open."))


def cancel_booking(booking: Booking, reason: str, actor_is_landlord: bool):
    """
Booking cancellation with a check against the 24-hour threshold based on check_in_at."""
    _check_dispute_status(booking)

    time_until_check_in = booking.check_in_at - timezone.now()

    if time_until_check_in < timedelta(hours=TIME_TO_CANCELLING_HOURS):
        raise ValidationError(
            _("You cannot cancel a reservation less than %(hours)s hours in advance.") %
            {'hours': TIME_TO_CANCELLING_HOURS}
        )

    if actor_is_landlord and not reason:
        raise ValidationError(_("Cancellation reason is required for landlord."))

    booking.status = BookingStatus.CANCELLED_BY_LANDLORD if actor_is_landlord else BookingStatus.CANCELLED_BY_TENANT
    booking.cancellation_reason = reason
    booking.save(update_fields=['status', 'cancellation_reason', 'updated_at'])


def confirm_booking(booking: Booking):
    """Booking confirmation."""
    _check_dispute_status(booking)

    if booking.status != BookingStatus.PENDING:
        raise ValidationError(_("Only bookings awaiting confirmation can be confirmed."))

    booking.status = BookingStatus.CONFIRMED
    booking.save(update_fields=['status', 'updated_at'])


def complete_booking(booking: Booking):
    """Change status to Complete."""
    if booking.status == BookingStatus.COMPLETED:
        return

    booking.status = BookingStatus.COMPLETED
    booking.save(update_fields=['status', 'updated_at'])


def auto_cancel_booking(booking: Booking):
    """Automatic cancellation of a booking not confirmed on time."""
    if booking.status == BookingStatus.PENDING:
        booking.status = BookingStatus.AUTO_CANCELLED
        booking.save(update_fields=['status', 'updated_at'])


def validate_status_transition(self, new_status):
    """
    State transition validator (State Machine).
    Called in the API method before saving.
    """
    if self.status == new_status:
        return

    # Prohibition of any changes if the booking is completed
    if self.status == BookingStatus.COMPLETED:
        raise ValidationError(_("Cannot modify a completed booking."))

    # Cancellation logic (24-hour check)
    if new_status in [BookingStatus.CANCELLED_BY_TENANT, BookingStatus.CANCELLED_BY_LANDLORD]:
        time_until_check_in = self.check_in_at - timezone.now()
        if time_until_check_in < timedelta(hours=TIME_TO_CANCELLING_HOURS):
            raise ValidationError(_("Cannot cancel booking less than %(hours)s hours before check-in.") %
                                  {'hours': TIME_TO_CANCELLING_HOURS})

    if new_status == BookingStatus.CANCELLED_BY_LANDLORD and not self.cancellation_reason:
        raise ValidationError(_("Cancellation reason is required for landlord."))

    # Additional protection (dispute)
    if self.disputes.filter(status=DisputeStatus.OPEN).exists():
        raise ValidationError(_("Cannot change status while a dispute is open."))
