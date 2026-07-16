from django.db.models import Q

from apps.bookings.choices import BookingStatus
from apps.bookings.models import Booking

ACTIVE_BOOKING_STATUSES = (BookingStatus.PENDING, BookingStatus.CONFIRMED)
COMPLETED_OR_ACTIVE_STATUSES = (
    ACTIVE_BOOKING_STATUSES,
    BookingStatus.COMPLETED,
)


def has_active_bookings_as_tenant(user) -> bool:
    return Booking.objects.filter(
        tenant=user, status__in=ACTIVE_BOOKING_STATUSES
    ).exists()


def has_active_bookings_as_landlord(user) -> bool:
    """A Booking entry refers to either a listing (apartment) or
    a room (hotel/hostel) — the owner is verified via both paths."""
    return Booking.objects.filter(
        Q(listing__owner=user) | Q(room__listing__owner=user),
        status__in=ACTIVE_BOOKING_STATUSES,
    ).exists()


def user_has_active_bookings(user) -> bool:
    """
    User blocking/deletion guard: prohibited if there is a booking in "pending"
    or "confirmed" status for either the renter or the landlord.
    """
    return has_active_bookings_as_tenant(user) or has_active_bookings_as_landlord(user)


def user_has_completed_booking_with_listing_owner(user, owner_id) -> bool:
    """
    For the public profile GET /api/v1/users/{id}/: access is granted
    if the current user (as a renter) has an active or
    completed booking for a listing/unit belonging to owner_id.
    """
    return Booking.objects.filter(
        Q(listing__owner_id=owner_id) | Q(room__listing__owner_id=owner_id),
        tenant=user,
        status__in=COMPLETED_OR_ACTIVE_STATUSES,
    ).exists()
