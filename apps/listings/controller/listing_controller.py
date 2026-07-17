from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.listings.dto import (
    ListingAmenitiesUpdateSerializer,
    ListingCreateSerializer,
    ListingDetailSerializer,
    ListingListSerializer,
    ListingStatusUpdateSerializer,
    ListingUpdateSerializer,
)
from apps.listings.paginations import ListingPagination
from apps.listings.repositories import ListingRepository
from apps.listings.services import ListingService
from apps.security.permissions import IsAdmin, IsLandlord, IsModerator, IsOwner


class ListingViewSet(viewsets.GenericViewSet):

    repository = ListingRepository()
    service = ListingService()
    pagination_class = ListingPagination

    def get_queryset(self):
        if self.action == "list":
            return self.service.list_listings(
                user=self.request.user, query_params=self.request.query_params
            )
        # Detail actions (update/destroy/status/toggle-active/amenities) must
        # see the object regardless of public visibility — access
        # is restricted by permission_classes, not the queryset.
        return self.repository.get_all_queryset()

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        if self.action == "create":
            return [IsLandlord()]
        if self.action == "destroy":
            return [(IsOwner | IsAdmin)()]
        if self.action in ("toggle_active", "amenities"):
            return [IsOwner()]
        if self.action == "mine":
            return [IsLandlord()]
        # update, partial_update, update_status
        return [(IsOwner | IsModerator | IsAdmin)()]

    def get_serializer_class(self):
        mapping = {
            "list": ListingListSerializer,
            "mine": ListingListSerializer,
            "create": ListingCreateSerializer,
            "update": ListingUpdateSerializer,
            "partial_update": ListingUpdateSerializer,
            "update_status": ListingStatusUpdateSerializer,
            "amenities": ListingAmenitiesUpdateSerializer,
        }
        return mapping.get(self.action, ListingDetailSerializer)

    # GET /api/v1/listings/
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        return self._paginated_response(queryset, ListingListSerializer)

    # GET /api/v1/listings/{id}/
    def retrieve(self, request, *args, **kwargs):
        listing = self.service.get_visible_detail(
            user=request.user,
            listing_id=kwargs["pk"],
            session_key=self._get_session_key(request),
        )
        if listing is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(ListingDetailSerializer(listing).data)

    # POST /api/v1/listings/
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        listing = self.service.create_listing(
            owner=request.user, validated_data=serializer.validated_data
        )
        return Response(
            ListingDetailSerializer(listing).data, status=status.HTTP_201_CREATED
        )

    # PATCH /api/v1/listings/{id}/
    def partial_update(self, request, *args, **kwargs):
        listing = self.get_object()
        serializer = self.get_serializer(listing, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        listing = self.service.update_listing(
            listing=listing,
            validated_data=serializer.validated_data,
            raw_data=request.data,
        )
        return Response(ListingDetailSerializer(listing).data)

    # DELETE /api/v1/listings/{id}/
    def destroy(self, request, *args, **kwargs):
        listing = self.get_object()
        self.service.delete_listing(listing)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # POST /api/v1/listings/{id}/toggle-active/
    @action(detail=True, methods=["post"], url_path="toggle-active")
    def toggle_active(self, request, pk=None):
        listing = self.service.toggle_active(self.get_object())
        return Response(ListingDetailSerializer(listing).data)

    # PATCH /api/v1/listings/{id}/status/
    @action(detail=True, methods=["patch"], url_path="status")
    def update_status(self, request, pk=None):
        listing = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        listing = self.service.update_status(
            listing=listing,
            new_status=serializer.validated_data["status"],
            actor=request.user,
        )
        return Response(ListingDetailSerializer(listing).data)

    # GET /api/v1/listings/mine/
    @action(detail=False, methods=["get"])
    def mine(self, request):
        queryset = self.service.get_mine(request.user)
        return self._paginated_response(queryset, ListingListSerializer)

    # PUT /api/v1/listings/{id}/amenities/
    @action(detail=True, methods=["put"])
    def amenities(self, request, pk=None):
        listing = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        listing = self.service.set_amenities(
            listing=listing, amenities=serializer.validated_data["amenity_ids"]
        )
        return Response(ListingDetailSerializer(listing).data)

    def _paginated_response(self, queryset, serializer_class):
        page = self.paginate_queryset(queryset)
        serializer = serializer_class(page if page is not None else queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @staticmethod
    def _get_session_key(request):
        session = getattr(request, "session", None)
        if session is None:
            return None
        if not session.session_key:
            session.save()
        return session.session_key
