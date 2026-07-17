from rest_framework import generics, status
from rest_framework.response import Response

from apps.listings.repositories import ListingRepository
from apps.pricing.dto import PriceHistoryCreateSerializer, PriceHistorySerializer
from apps.pricing.models import PriceHistory
from apps.pricing.services import PriceHistoryService
from apps.security.permissions import IsAdmin, IsOwner


class PriceSetView(generics.GenericAPIView):
    """POST /api/v1/listings/{listing_id}/price/ — The owner sets a new price.
    They create a record in PriceHistory."""

    serializer_class = PriceHistoryCreateSerializer
    permission_classes = [IsOwner]

    listing_repository = ListingRepository()
    service = PriceHistoryService()

    def post(self, request, *args, **kwargs):
        listing = self.listing_repository.get_by_id_any(kwargs["listing_id"])
        if listing is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, listing)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        price_history = self.service.set_price_for_listing(
            listing=listing, changed_by=request.user, **serializer.validated_data
        )
        return Response(
            PriceHistorySerializer(price_history).data, status=status.HTTP_201_CREATED
        )


class PriceHistoryListView(generics.ListAPIView):
    """GET /api/v1/listings/{listing_id}/price-history/ — Owner/Admin."""

    serializer_class = PriceHistorySerializer
    permission_classes = [IsOwner | IsAdmin]

    listing_repository = ListingRepository()
    service = PriceHistoryService()

    def get_queryset(self):
        listing = self.listing_repository.get_by_id_any(self.kwargs["listing_id"])
        if listing is None:
            return PriceHistory.objects.none()
        self.check_object_permissions(self.request, listing)
        return self.service.get_history_for_listing(listing.id)
