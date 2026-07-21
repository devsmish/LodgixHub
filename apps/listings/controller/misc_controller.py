from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.bookings.dto import BookingSerializer
from apps.listings.repositories import ListingRepository


class AvailabilityCalendarView(generics.GenericAPIView):
    """GET /api/v1/listings/{listing_id}/availability-calendar/?month=YYYY-MM"""

    permission_classes = [AllowAny]
    listing_repository = ListingRepository()

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "month", str, description="YYYY-MM format; defaults to the current month."
            )
        ],
        responses={
            200: OpenApiResponse(
                response={
                    "type": "object",
                    "properties": {
                        "year": {"type": "integer"},
                        "month": {"type": "integer"},
                        "days": {
                            "type": "object",
                            "additionalProperties": {"type": "boolean"},
                            "description": "Key — day of the month, value — whether the day is available",
                        },
                    },
                }
            )
        },
    )
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
    serializer_class = BookingSerializer
    listing_repository = ListingRepository()

    def get_queryset(self):
        listing = self.listing_repository.get_by_id_any(self.kwargs["listing_id"])
        if listing is None:
            raise NotFound()
        if listing.owner_id != self.request.user.id:
            raise PermissionDenied(
                "Only the listing owner can view its bookings."
            )

        from apps.bookings.models import Booking

        listing_id = self.kwargs["listing_id"]
        return Booking.objects.filter(
            Q(listing_id=listing_id) | Q(room__listing_id=listing_id)
        )

