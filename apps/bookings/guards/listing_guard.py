from django.db.models import Q

from apps.bookings.choices import BookingStatus
from apps.bookings.models import Booking

ACTIVE_BOOKING_STATUSES = (BookingStatus.PENDING, BookingStatus.CONFIRMED)


def listing_has_active_bookings(listing) -> bool:
    """Deleting a listing is prohibited if there is a booking with a "pending" or "confirmed" status
    — whether for the listing (apartment) itself or for any of its rooms (hotel/hostel).
    """
    return Booking.objects.filter(
        Q(listing=listing) | Q(room__listing=listing),
        status__in=ACTIVE_BOOKING_STATUSES,
    ).exists()


def room_has_active_bookings(room) -> bool:
    """Deleting a Room is prohibited if there are pending or
    confirmed bookings for that room for future dates."""
    return Booking.objects.filter(
        room=room, status__in=ACTIVE_BOOKING_STATUSES
    ).exists()
