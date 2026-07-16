from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.bookings.dto import CancellationReasonSerializer
from apps.bookings.models import CancellationReason
from apps.security.permissions import IsAdmin


class CancellationReasonViewSet(viewsets.ModelViewSet):
    """/api/v1/cancellation-reasons/ — справочник (ТЗ 2.12).
    GET — Авторизованный (не AllowAny — так в ТЗ). POST/PATCH/DELETE — Админ.
    DELETE — soft delete (унаследован от BaseModel)."""

    queryset = CancellationReason.objects.all()
    serializer_class = CancellationReasonSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAdmin()]
        return [IsAuthenticated()]
