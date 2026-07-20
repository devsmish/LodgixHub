from apps.bookings.models import Booking


class BookingRepository:

    @staticmethod
    def get_all_queryset():
        return Booking.objects.select_related(
            "tenant", "listing", "room", "room__listing"
        )

    @staticmethod
    def get_by_id(booking_id):
        return (
            Booking.objects.filter(id=booking_id)
            .select_related("tenant", "listing", "room", "room__listing")
            .first()
        )
