from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.bookings.dto import (
    BookingCancelSerializer,
    BookingCreateSerializer,
    BookingSerializer,
)
from apps.bookings.models import CancellationReason, Booking
from apps.bookings.repositories import BookingRepository
from apps.bookings.services import BookingService
from apps.security.constants import GROUP_ADMIN


class BookingViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):

    permission_classes = [IsAuthenticated]
    queryset = Booking.objects.all()
    repository = BookingRepository()
    service = BookingService()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return Booking.objects.none()
        return self.service.list_for_user(self.request.user)

    def get_serializer_class(self):
        mapping = {
            "create": BookingCreateSerializer,
            "cancel": BookingCancelSerializer,
        }
        return mapping.get(self.action, BookingSerializer)

    def get_object(self):
        booking = self.repository.get_by_id(self.kwargs["pk"])
        if booking is None:
            raise NotFound()
        self._guard_participant_or_admin(booking)
        return booking

    def _guard_participant_or_admin(self, booking):
        user = self.request.user
        is_admin = user.is_superuser or user.groups.filter(name=GROUP_ADMIN).exists()
        if not (self.service.is_participant(booking, user) or is_admin):
            raise PermissionDenied("You are not a participant in this booking.")

    # GET /api/v1/bookings/
    def list(self, request, *args, **kwargs):
        serializer = BookingSerializer(self.get_queryset(), many=True)
        return Response(serializer.data)

    # GET /api/v1/bookings/{id}/
    def retrieve(self, request, *args, **kwargs):
        booking = self.get_object()
        return Response(BookingSerializer(booking).data)

    # POST /api/v1/bookings/
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        booking = self.service.create_booking(
            tenant=request.user,
            listing_id=data.get("listing_id"),
            room_id=data.get("room_id"),
            check_in_date=data["check_in_date"],
            check_out_date=data["check_out_date"],
            guests_count=data["guests_count"],
        )
        return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)

    # POST /api/v1/bookings/{id}/confirm/
    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        booking = self.get_object()
        booking = self.service.confirm(booking=booking, actor=request.user)
        return Response(BookingSerializer(booking).data)

    # POST /api/v1/bookings/{id}/reject/
    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        booking = self.get_object()
        booking = self.service.reject(booking=booking, actor=request.user)
        return Response(BookingSerializer(booking).data)

    # POST /api/v1/bookings/{id}/cancel/
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cancellation_reason = self._resolve_cancellation_reason(
            serializer.validated_data.get("cancellation_reason_id")
        )
        booking = self.service.cancel(
            booking=booking, actor=request.user, cancellation_reason=cancellation_reason
        )
        return Response(BookingSerializer(booking).data)

    @staticmethod
    def _resolve_cancellation_reason(reason_id):
        if reason_id is None:
            return None
        reason = CancellationReason.objects.filter(id=reason_id).first()
        if reason is None:
            raise NotFound("The reason for the cancellation was not found.")
        return reason
