from django.db.models import Q
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.listings.repositories import ListingRepository


class AvailabilityCalendarView(generics.GenericAPIView):
    """GET /api/v1/listings/{listing_id}/availability-calendar/?month=YYYY-MM"""

    permission_classes = [AllowAny]
    listing_repository = ListingRepository()

    def get(self, request, *args, **kwargs):
        listing = self.listing_repository.get_by_id_any(kwargs["listing_id"])
        if listing is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        year, month = self._parse_month(request.query_params.get("month"))

        from apps.bookings.guards import get_listing_calendar

        days = get_listing_calendar(listing, year, month)
        return Response({"year": year, "month": month, "days": days})

    @staticmethod
    def _parse_month(month_param):
        if not month_param:
            today = timezone.localdate()
            return today.year, today.month
        try:
            year_str, month_str = month_param.split("-")
            return int(year_str), int(month_str)
        except (ValueError, AttributeError) as exc:
            raise DRFValidationError({"month": "Format expected YYYY-MM."}) from exc


class ListingBookingsView(generics.ListAPIView):
    """GET /api/v1/listings/{listing_id}/bookings/ — owner."""

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from apps.bookings.models import Booking

        listing_id = self.kwargs["listing_id"]
        return Booking.objects.filter(
            Q(listing_id=listing_id) | Q(room__listing_id=listing_id)
        )
