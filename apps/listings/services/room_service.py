from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.listings.errors import RoomHasActiveBookingsError
from apps.listings.models import Room
from apps.listings.repositories import RoomRepository


class RoomService:

    def __init__(self, repository: RoomRepository = None):
        self.repository = repository or RoomRepository()

    def list_for_listing(self, *, listing_id, check_in=None, check_out=None):
        rooms = list(self.repository.get_for_listing(listing_id))
        if check_in and check_out:
            self._annotate_availability(rooms, check_in, check_out)
        return rooms

    @staticmethod
    def _annotate_availability(rooms, check_in, check_out):
        from django.db.models import Count

        from apps.bookings.guards.availability_guard import ACTIVE_BOOKING_STATUSES
        from apps.bookings.models import Booking

        room_ids = [room.id for room in rooms]
        busy_counts = dict(
            Booking.objects.filter(
                room_id__in=room_ids,
                status__in=ACTIVE_BOOKING_STATUSES,
                check_in_date__lt=check_out,
                check_out_date__gt=check_in,
            )
            .values("room_id")
            .annotate(busy=Count("id"))
            .values_list("room_id", "busy")
        )
        for room in rooms:
            busy = busy_counts.get(room.id, 0)
            room._available_count = max(room.rooms_available_count - busy, 0)

    @transaction.atomic
    def create_room(self, *, listing, validated_data):
        room = Room(listing=listing, **validated_data)
        return self._save_or_raise(room)

    @transaction.atomic
    def update_room(self, *, room, validated_data):
        for field, value in validated_data.items():
            setattr(room, field, value)
        return self._save_or_raise(room)

    @staticmethod
    def _save_or_raise(room):
        """Translates a Django ValidationError into a proper DRF response (400) instead of a 500."""
        try:
            room.save()
        except DjangoValidationError as exc:
            detail = (
                exc.message_dict
                if hasattr(exc, "message_dict")
                else {"detail": exc.messages}
            )
            raise DRFValidationError(detail) from exc
        return room

    @transaction.atomic
    def delete_room(self, room):
        """It is blocked if there is a booking with a "pending"
        or "confirmed" status for future dates."""
        from apps.bookings.guards.listing_guard import room_has_active_bookings

        if room_has_active_bookings(room):
            raise RoomHasActiveBookingsError()
        room.delete()
        return room
