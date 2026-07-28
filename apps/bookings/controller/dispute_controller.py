from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.bookings.dto import (
    DisputeCreateSerializer,
    DisputeEvidenceCreateSerializer,
    DisputeEvidenceSerializer,
    DisputeResolveSerializer,
    DisputeSerializer,
)
from apps.bookings.errors import convert_django_validation_error
from apps.bookings.repositories import BookingRepository, DisputeRepository
from apps.bookings.services import (
    BookingService,
    add_evidence,
    open_dispute,
    resolve_dispute,
    start_review,
)
from apps.security.permissions import IsAdmin, IsModerator
from apps.security.constants import GROUP_ADMIN, GROUP_MODERATOR


def _is_moderator_or_admin(user) -> bool:
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=(GROUP_MODERATOR, GROUP_ADMIN)).exists()


class BookingDisputesView(generics.ListCreateAPIView):
    """GET/POST /api/v1/bookings/{booking_id}/disputes/ — booking participants only."""

    permission_classes = [IsAuthenticated]

    booking_repository = BookingRepository()
    dispute_repository = DisputeRepository()
    booking_service = BookingService()

    def get_serializer_class(self):
        return (
            DisputeCreateSerializer
            if self.request.method == "POST"
            else DisputeSerializer
        )

    def get_queryset(self):
        booking = self._get_visible_booking()
        return self.dispute_repository.get_for_booking(booking.id)

    def create(self, request, *args, **kwargs):
        booking = self._get_participant_booking()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            dispute = open_dispute(
                booking=booking,
                opened_by=request.user,
                reason_category=serializer.validated_data["reason_category"],
                reason=serializer.validated_data["reason"],
                claim_amount=serializer.validated_data.get("claim_amount", 0),
            )
        except DjangoValidationError as exc:
            raise convert_django_validation_error(exc) from exc

        return Response(DisputeSerializer(dispute).data, status=status.HTTP_201_CREATED)

    def _get_participant_booking(self):
        booking = self.booking_repository.get_by_id(self.kwargs["booking_id"])
        if booking is None:
            raise NotFound()
        if not self.booking_service.is_participant(booking, self.request.user):
            raise PermissionDenied("You are not a participant in this booking.")
        return booking

    def _get_visible_booking(self):
        booking = self.booking_repository.get_by_id(self.kwargs["booking_id"])
        if booking is None:
            raise NotFound()
        if not (
            self.booking_service.is_participant(booking, self.request.user)
            or _is_moderator_or_admin(self.request.user)
        ):
            raise PermissionDenied("You are not a participant in this booking.")
        return booking


class DisputeViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """
    GET /api/v1/disputes/ — moderation queue (moderator/admin only),
    open and pending disputes — first
    GET /api/v1/disputes/{id}/ — A booking participant or a moderator/admin.
    review/resolve — moderator/admin only"""

    repository = DisputeRepository()
    booking_service = BookingService()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from django.db.models import Case, IntegerField, Value, When

        from apps.bookings.choices import DisputeStatus
        from apps.bookings.models import Dispute

        queryset = Dispute.objects.all()
        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)

        # Open and pending disputes are at the front of the queue.
        priority = Case(
            When(status=DisputeStatus.OPEN, then=Value(0)),
            When(status=DisputeStatus.UNDER_REVIEW, then=Value(1)),
            default=Value(2),
            output_field=IntegerField(),
        )
        return queryset.order_by(priority, "-created_at")

    def get_permissions(self):
        if self.action in ("list", "review", "resolve"):
            return [(IsModerator | IsAdmin)()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "resolve":
            return DisputeResolveSerializer
        return DisputeSerializer

    def get_object(self):
        dispute = self.repository.get_by_id(self.kwargs["pk"])
        if dispute is None:
            raise NotFound()

        # review/resolve are already filtered out at the get_permissions() level
        # (moderator/admin only) — here we further restrict retrieve specifically:
        # booking participant or the same moderator/admin, not just any authenticated user.
        if self.action == "retrieve" and not (
            self.booking_service.is_participant(dispute.booking, self.request.user)
            or _is_moderator_or_admin(self.request.user)
        ):
            raise PermissionDenied("You are not a participant in this booking.")
        return dispute

    # PATCH /api/v1/disputes/{id}/review/
    @action(detail=True, methods=["patch"])
    def review(self, request, pk=None):
        dispute = self.get_object()
        try:
            dispute = start_review(dispute=dispute, moderator=request.user)
        except DjangoValidationError as exc:
            raise convert_django_validation_error(exc) from exc
        return Response(DisputeSerializer(dispute).data)

    # POST /api/v1/disputes/{id}/resolve/
    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        dispute = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            dispute = resolve_dispute(
                dispute=dispute,
                moderator=request.user,
                new_status=serializer.validated_data["status"],
                resolution_favor=serializer.validated_data["resolution_favor"],
                resolution_amount=serializer.validated_data.get("resolution_amount"),
                notes=serializer.validated_data.get("notes", ""),
            )
        except DjangoValidationError as exc:
            raise convert_django_validation_error(exc) from exc

        return Response(DisputeSerializer(dispute).data)


class DisputeEvidenceView(generics.ListCreateAPIView):
    """GET/POST /api/v1/disputes/{dispute_id}/evidence/ — only
    participants to the dispute or the moderator/admin."""

    permission_classes = [IsAuthenticated]

    dispute_repository = DisputeRepository()
    booking_service = BookingService()

    def get_serializer_class(self):
        return (
            DisputeEvidenceCreateSerializer
            if self.request.method == "POST"
            else DisputeEvidenceSerializer
        )

    def get_queryset(self):
        dispute = self._get_visible_dispute()
        return self.dispute_repository.get_evidence_for_dispute(dispute.id)

    def create(self, request, *args, **kwargs):
        dispute = self._get_participant_dispute()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            evidence = add_evidence(
                dispute=dispute,
                uploaded_by=request.user,
                url=serializer.validated_data["url"],
                description=serializer.validated_data.get("description", ""),
            )
        except DjangoValidationError as exc:
            raise convert_django_validation_error(exc) from exc

        return Response(
            DisputeEvidenceSerializer(evidence).data, status=status.HTTP_201_CREATED
        )

    def _get_participant_dispute(self):
        dispute = self.dispute_repository.get_by_id(self.kwargs["dispute_id"])
        if dispute is None:
            raise NotFound()
        if not self.booking_service.is_participant(dispute.booking, self.request.user):
            raise PermissionDenied("You are not a participant in this booking.")
        return dispute

    def _get_visible_dispute(self):
        dispute = self.dispute_repository.get_by_id(self.kwargs["dispute_id"])
        if dispute is None:
            raise NotFound()
        if not (
            self.booking_service.is_participant(dispute.booking, self.request.user)
            or _is_moderator_or_admin(self.request.user)
        ):
            raise PermissionDenied("You are not a participant in this booking.")
        return dispute


class DisputeEvidenceDetailView(generics.DestroyAPIView):
    """DELETE /api/v1/disputes/{dispute_id}/evidence/{pk}/ — the uploader
    or the moderator/admin."""

    permission_classes = [IsAuthenticated]
    serializer_class = DisputeEvidenceSerializer
    dispute_repository = DisputeRepository()

    def get_queryset(self):
        return self.dispute_repository.get_evidence_for_dispute(
            self.kwargs["dispute_id"]
        )

    def get_object(self):
        evidence = self.get_queryset().filter(pk=self.kwargs["pk"]).first()
        if evidence is None:
            raise NotFound()

        user = self.request.user
        if not (evidence.uploaded_by_id == user.id or _is_moderator_or_admin(user)):
            raise PermissionDenied(
                "Only the uploader can delete the proof."
            )
        return evidence
