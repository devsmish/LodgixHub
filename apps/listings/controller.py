from rest_framework import generics, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated

from apps.listings.models import Amenity, Listing, Room
from apps.pricing.models import PriceHistory


class ListingViewSet(viewsets.ModelViewSet):
    queryset = Listing.objects.all()
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        return super().get_permissions()

    def destroy(self, request, *args, **kwargs):
        raise NotImplementedError

    @action(detail=True, methods=["post"], url_path="toggle-active")
    def toggle_active(self, request, pk=None):
        raise NotImplementedError

    @action(detail=True, methods=["patch"])
    def status(self, request, pk=None):
        raise NotImplementedError

    @action(detail=False, methods=["get"])
    def mine(self, request):
        raise NotImplementedError

    @action(detail=True, methods=["put"])
    def amenities(self, request, pk=None):
        raise NotImplementedError


class AmenityViewSet(viewsets.ModelViewSet):

    queryset = Amenity.objects.all()
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action == "list":
            return [AllowAny()]
        return super().get_permissions()


class RoomListCreateView(generics.ListCreateAPIView):

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Room.objects.filter(listing_id=self.kwargs["listing_id"])


class RoomDetailView(generics.RetrieveUpdateDestroyAPIView):

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Room.objects.filter(listing_id=self.kwargs["listing_id"])

    def destroy(self, request, *args, **kwargs):
        raise NotImplementedError


class AvailabilityCalendarView(generics.ListAPIView):

    permission_classes = [AllowAny]

    def get_queryset(self):
        raise NotImplementedError


class ListingBookingsView(generics.ListAPIView):

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from apps.bookings.models import Booking

        return Booking.objects.filter(listing_id=self.kwargs["listing_id"])


class PriceSetView(generics.CreateAPIView):

    permission_classes = [IsAuthenticated]
    queryset = PriceHistory.objects.all()


class PriceHistoryListView(generics.ListAPIView):

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PriceHistory.objects.filter(listing_id=self.kwargs["listing_id"])
