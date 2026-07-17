from rest_framework import generics, status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.listings.dto import RoomCreateSerializer, RoomSerializer, RoomUpdateSerializer
from apps.listings.repositories import ListingRepository, RoomRepository
from apps.listings.services import RoomService


class RoomListCreateView(generics.GenericAPIView):
    """GET/POST /api/v1/listings/{listing_id}/rooms/ — only the listing owner
    can create rooms; the list is open to anyone."""

    permission_classes = [IsAuthenticated]

    listing_repository = ListingRepository()
    room_repository = RoomRepository()
    service = RoomService()

    def get_permissions(self):
        if self.request.method == "GET":
            from rest_framework.permissions import AllowAny

            return [AllowAny()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        return RoomCreateSerializer if self.request.method == "POST" else RoomSerializer

    def get(self, request, *args, **kwargs):
        rooms = self.service.list_for_listing(
            listing_id=kwargs["listing_id"],
            check_in=request.query_params.get("check_in"),
            check_out=request.query_params.get("check_out"),
        )
        return Response(RoomSerializer(rooms, many=True).data)

    def post(self, request, *args, **kwargs):
        listing = self._get_owned_listing(request, kwargs["listing_id"])

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        room = self.service.create_room(
            listing=listing, validated_data=serializer.validated_data
        )
        return Response(RoomSerializer(room).data, status=status.HTTP_201_CREATED)

    def _get_owned_listing(self, request, listing_id):
        listing = self.listing_repository.get_by_id_any(listing_id)
        if listing is None:
            raise NotFound()
        if listing.owner_id != request.user.id:
            raise PermissionDenied(
                "Only the owner of the listing can manage the rooms."
            )
        return listing


class RoomDetailView(generics.GenericAPIView):
    """PATCH/DELETE /api/v1/listings/{listing_id}/rooms/{pk}/  — only the owner."""

    permission_classes = [IsAuthenticated]
    serializer_class = RoomUpdateSerializer

    listing_repository = ListingRepository()
    room_repository = RoomRepository()
    service = RoomService()

    def patch(self, request, *args, **kwargs):
        room = self._get_owned_room(request, kwargs["listing_id"], kwargs["pk"])
        serializer = self.get_serializer(room, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        room = self.service.update_room(
            room=room, validated_data=serializer.validated_data
        )
        return Response(RoomSerializer(room).data)

    def delete(self, request, *args, **kwargs):
        room = self._get_owned_room(request, kwargs["listing_id"], kwargs["pk"])
        self.service.delete_room(room)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _get_owned_room(self, request, listing_id, room_id):
        listing = self.listing_repository.get_by_id_any(listing_id)
        if listing is None:
            raise NotFound()
        if listing.owner_id != request.user.id:
            raise PermissionDenied(
                "Only the owner of the listing can manage the rooms."
            )
        room = self.room_repository.get_by_id_for_listing(listing_id, room_id)
        if room is None:
            raise NotFound()
        return room
