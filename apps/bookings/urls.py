from django.urls import path
from rest_framework.routers import SimpleRouter

from apps.bookings.controller import (
    BookingDisputesView,
    BookingViewSet,
    CancellationReasonViewSet,
    DisputeEvidenceDetailView,
    DisputeEvidenceView,
    DisputeViewSet,
)

app_name = "bookings"

router = SimpleRouter()
router.register("bookings", BookingViewSet, basename="booking")
router.register("cancellation-reasons", CancellationReasonViewSet, basename="cancellation-reason")
router.register("disputes", DisputeViewSet, basename="dispute")

urlpatterns = router.urls + [
    path(
        "bookings/<uuid:booking_id>/disputes/",
        BookingDisputesView.as_view(),
        name="booking-disputes",
    ),
    path(
        "disputes/<uuid:dispute_id>/evidence/",
        DisputeEvidenceView.as_view(),
        name="dispute-evidence",
    ),
    path(
        "disputes/<uuid:dispute_id>/evidence/<uuid:pk>/",
        DisputeEvidenceDetailView.as_view(),
        name="dispute-evidence-detail",
    ),
]
