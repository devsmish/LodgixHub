from rest_framework import generics, status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.content.dto import (
    PhotoCreateSerializer,
    PhotoSerializer,
    PhotoUpdateSerializer,
)
from apps.content.repositories import PhotoRepository
from apps.content.services import PhotoService
from apps.listings.repositories import ListingRepository
from apps.security.constants import GROUP_ADMIN


class PhotoListCreateView(generics.GenericAPIView):
    """GET/POST /api/v1/listings/{listing_id}/photos/  — GET is
    open to anyone; POST is restricted to the ad owner."""

    permission_classes = [IsAuthenticated]

    listing_repository = ListingRepository()
    repository = PhotoRepository()
    service = PhotoService()

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        return (
            PhotoCreateSerializer if self.request.method == "POST" else PhotoSerializer
        )

    def get(self, request, *args, **kwargs):
        photos = self.service.list_for_listing(kwargs["listing_id"])
        return Response(PhotoSerializer(photos, many=True).data)

    def post(self, request, *args, **kwargs):
        listing = self._get_owned_listing(request, kwargs["listing_id"])

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        photo = self.service.create_photo(
            listing=listing, uploaded_by=request.user, **serializer.validated_data
        )
        return Response(PhotoSerializer(photo).data, status=status.HTTP_201_CREATED)

    def _get_owned_listing(self, request, listing_id):
        listing = self.listing_repository.get_by_id_any(listing_id)
        if listing is None:
            raise NotFound()
        if listing.owner_id != request.user.id:
            raise PermissionDenied("Only the owner of the listing can upload photos.")
        return listing


class PhotoDetailView(generics.GenericAPIView):
    """PATCH /api/v1/listings/{listing_id}/photos/{pk}/ — owner.
    DELETE — owner/admin. Hard delete — the `post_delete` signal (`apps.content.signals`)
    already removes the file from S3/local storage."""

    permission_classes = [IsAuthenticated]
    serializer_class = PhotoUpdateSerializer

    listing_repository = ListingRepository()
    repository = PhotoRepository()
    service = PhotoService()

    def patch(self, request, *args, **kwargs):
        photo = self._get_photo_for_action(
            request, kwargs["listing_id"], kwargs["pk"], allow_admin=False
        )
        serializer = self.get_serializer(photo, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        photo = self.service.update_photo(photo=photo, **serializer.validated_data)
        return Response(PhotoSerializer(photo).data)

    def delete(self, request, *args, **kwargs):
        photo = self._get_photo_for_action(
            request, kwargs["listing_id"], kwargs["pk"], allow_admin=True
        )
        photo.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _get_photo_for_action(self, request, listing_id, photo_id, *, allow_admin):
        listing = self.listing_repository.get_by_id_any(listing_id)
        if listing is None:
            raise NotFound()

        is_owner = listing.owner_id == request.user.id
        is_admin = allow_admin and (
            request.user.is_superuser
            or request.user.groups.filter(name=GROUP_ADMIN).exists()
        )
        if not (is_owner or is_admin):
            raise PermissionDenied(
                "Only the listing owner can manage the photos."
                + (" or admin (for deletion)." if allow_admin else ".")
            )

        photo = self.repository.get_by_id_for_listing(listing_id, photo_id)
        if photo is None:
            raise NotFound()
        return photo
