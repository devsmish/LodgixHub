from rest_framework import generics, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from apps.bookings.models import Booking, CancellationReason, Dispute, DisputeEvidence


class BookingViewSet(viewsets.GenericViewSet):

    queryset = Booking.objects.all()
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        raise NotImplementedError

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        raise NotImplementedError

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        raise NotImplementedError


class CancellationReasonViewSet(viewsets.ModelViewSet):

    queryset = CancellationReason.objects.all()
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action == "list":
            from rest_framework.permissions import AllowAny

            return [AllowAny()]
        return super().get_permissions()


class BookingDisputesView(generics.ListCreateAPIView):

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Dispute.objects.filter(booking_id=self.kwargs["booking_id"])


class DisputeViewSet(viewsets.GenericViewSet):

    queryset = Dispute.objects.all()
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["patch"])
    def review(self, request, pk=None):
        raise NotImplementedError

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        raise NotImplementedError


class DisputeEvidenceView(generics.ListCreateAPIView):

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return DisputeEvidence.objects.filter(dispute_id=self.kwargs["dispute_id"])


class DisputeEvidenceDetailView(generics.DestroyAPIView):

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return DisputeEvidence.objects.filter(dispute_id=self.kwargs["dispute_id"])
