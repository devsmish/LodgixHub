from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.bookings.dto import CancellationReasonSerializer
from apps.bookings.models import CancellationReason
from apps.security.permissions import IsAdmin


class CancellationReasonViewSet(viewsets.ModelViewSet):
    """/api/v1/cancellation-reasons/ — reference data.
    GET — Authorized. POST/PATCH/DELETE — Admin.
    DELETE — soft delete."""

    queryset = CancellationReason.objects.all()
    serializer_class = CancellationReasonSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAdmin()]
        return [IsAuthenticated()]
