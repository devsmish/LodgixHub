from django.urls import path
from rest_framework.routers import SimpleRouter

from apps.listings.controller import (
    AmenityViewSet,
    AvailabilityCalendarView,
    ListingBookingsView,
    ListingViewSet,
    RoomDetailView,
    RoomListCreateView,
)

app_name = "listings"

router = SimpleRouter()
router.register("listings", ListingViewSet, basename="listing")
router.register("amenities", AmenityViewSet, basename="amenity")

urlpatterns = router.urls + [
    path(
        "listings/<uuid:listing_id>/rooms/",
        RoomListCreateView.as_view(),
        name="listing-rooms",
    ),
    path(
        "listings/<uuid:listing_id>/rooms/<uuid:pk>/",
        RoomDetailView.as_view(),
        name="listing-room-detail",
    ),
    path(
        "listings/<uuid:listing_id>/availability-calendar/",
        AvailabilityCalendarView.as_view(),
        name="listing-availability",
    ),
    path(
        "listings/<uuid:listing_id>/bookings/",
        ListingBookingsView.as_view(),
        name="listing-bookings",
    ),
]
