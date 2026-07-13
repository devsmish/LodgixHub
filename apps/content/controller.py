from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from apps.content.models import Photo


class PhotoListCreateView(generics.ListCreateAPIView):

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Photo.objects.filter(listing_id=self.kwargs["listing_id"])


class PhotoDetailView(generics.RetrieveUpdateDestroyAPIView):

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Photo.objects.filter(listing_id=self.kwargs["listing_id"])
