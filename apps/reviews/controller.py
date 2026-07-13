from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated

from apps.reviews.models import Review


class ReviewViewSet(viewsets.GenericViewSet):

    queryset = Review.objects.all()
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        return super().get_permissions()

    @action(detail=False, methods=["get"])
    def mine(self, request):
        raise NotImplementedError

    @action(detail=False, methods=["get"])
    def landlord(self, request):
        raise NotImplementedError

    @action(detail=True, methods=["post"])
    def respond(self, request, pk=None):
        raise NotImplementedError

    @action(detail=True, methods=["patch"])
    def status(self, request, pk=None):
        raise NotImplementedError
