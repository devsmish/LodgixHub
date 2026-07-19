from datetime import datetime, timedelta

from django.utils import timezone

from apps.bookings.constants import (
    AUTO_CANCEL_TIMEOUT_MINUTES,
    BUSINESS_HOURS_END,
    BUSINESS_HOURS_START,
)


def calculate_auto_cancel_deadline(created_at: datetime) -> datetime:
    """
    Unified algorithm:
    The auto-cancellation deadline is the moment when the accumulated time *within* business hours
    (BUSINESS_HOURS_START..BUSINESS_HOURS_END) since the booking was created reaches
    AUTO_CANCEL_TIMEOUT_MINUTES. If the time remaining until the end of business hours
    on the current day is insufficient, the remainder carries over to 09:00 the following day.

    The time zone used is the server's (settings.TIME_ZONE), not the listing's: the Listing/Room
    model does not yet have its own time zone field.

    Examples:
      14:00 (time available until 21:00) -> 14:30 (no carry-over)
      20:50 (only 10 minutes available)  -> 09:20 the next day
      23:00 (outside business hours)     -> 09:30 the next day
    """
    remaining_minutes = AUTO_CANCEL_TIMEOUT_MINUTES
    current = _clamp_to_business_hours(timezone.localtime(created_at))

    while True:
        business_end = current.replace(
            hour=BUSINESS_HOURS_END, minute=0, second=0, microsecond=0
        )
        available_minutes = (business_end - current).total_seconds() / 60

        if available_minutes >= remaining_minutes:
            return current + timedelta(minutes=remaining_minutes)

        remaining_minutes -= available_minutes
        current = (current + timedelta(days=1)).replace(
            hour=BUSINESS_HOURS_START, minute=0, second=0, microsecond=0
        )


def _clamp_to_business_hours(moment: datetime) -> datetime:
    """If the moment falls outside business hours, it is shifted to the nearest start time:
    before 09:00 on the same day → 09:00 on the same day; after 21:00 → 09:00
    on the next day."""
    business_start = moment.replace(
        hour=BUSINESS_HOURS_START, minute=0, second=0, microsecond=0
    )
    business_end = moment.replace(
        hour=BUSINESS_HOURS_END, minute=0, second=0, microsecond=0
    )
    if moment < business_start:
        return business_start
    if moment >= business_end:
        return (moment + timedelta(days=1)).replace(
            hour=BUSINESS_HOURS_START, minute=0, second=0, microsecond=0
        )
    return moment
