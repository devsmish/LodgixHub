from rest_framework import mixins, viewsets
from rest_framework.permissions import AllowAny

from apps.listings.dto import AmenitySerializer, AmenityUpdateSerializer
from apps.listings.repositories import AmenityRepository
from apps.security.permissions import IsAdmin


class AmenityViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """/api/v1/amenities/ — amenities reference. GET — anyone,
    POST/PATCH/DELETE — admin only. DELETE — soft delete."""

    repository = AmenityRepository()

    def get_queryset(self):
        return self.repository.get_active_queryset()

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        return [IsAdmin()]

    def get_serializer_class(self):
        if self.action in ("update", "partial_update"):
            return AmenityUpdateSerializer
        return AmenitySerializer
