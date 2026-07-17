from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.bookings.repositories import BookingRepository
from apps.reviews.dto import (
    ReviewCreateSerializer,
    ReviewRespondSerializer,
    ReviewSerializer,
    ReviewStatusUpdateSerializer,
    ReviewUpdateSerializer,
)
from apps.reviews.repositories import ReviewRepository
from apps.reviews.services import ReviewService
from apps.security.permissions import IsAdmin, IsLandlord, IsModerator, IsOwner


class ReviewViewSet(viewsets.GenericViewSet):

    repository = ReviewRepository()
    service = ReviewService()
    booking_repository = BookingRepository()

    def get_permissions(self):
        if self.action == "list":
            # with listing_id — public (published only);
            # without listing_id — moderation queue, moderator/admin only.
            if self.request.query_params.get("listing_id"):
                return [AllowAny()]
            return [(IsModerator | IsAdmin)()]
        if self.action == "retrieve":
            return [AllowAny()]
        if self.action == "partial_update":
            return [IsOwner()]
        if self.action == "destroy":
            return [(IsOwner | IsAdmin)()]
        if self.action == "update_status":
            return [(IsModerator | IsAdmin)()]
        if self.action == "landlord":
            return [IsLandlord()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        mapping = {
            "create": ReviewCreateSerializer,
            "partial_update": ReviewUpdateSerializer,
            "respond": ReviewRespondSerializer,
            "update_status": ReviewStatusUpdateSerializer,
        }
        return mapping.get(self.action, ReviewSerializer)

    def get_object(self):
        review = self.repository.get_by_id(self.kwargs["pk"])
        if review is None:
            raise NotFound()
        self.check_object_permissions(self.request, review)
        return review

    # GET /api/v1/reviews/?listing_id=  |  GET /api/v1/reviews/ (moderation)
    def list(self, request, *args, **kwargs):
        listing_id = request.query_params.get("listing_id")
        if listing_id:
            queryset = self.service.list_published_for_listing(listing_id)
        else:
            queryset = self.service.list_for_moderation()
        return Response(ReviewSerializer(queryset, many=True).data)

    # GET /api/v1/reviews/{id}/
    def retrieve(self, request, *args, **kwargs):
        return Response(ReviewSerializer(self.get_object()).data)

    # POST /api/v1/reviews/
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        booking = self.booking_repository.get_by_id(data["booking_id"])
        if booking is None:
            raise NotFound("Reservation not found.")

        review = self.service.create_review(
            author=request.user,
            booking=booking,
            rating=data["rating"],
            comment=data.get("comment", ""),
        )
        return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)

    # PATCH /api/v1/reviews/{id}/
    def partial_update(self, request, *args, **kwargs):
        review = self.get_object()
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        review = self.service.update_review(review=review, **serializer.validated_data)
        return Response(ReviewSerializer(review).data)

    # DELETE /api/v1/reviews/{id}/ — hard delete
    def destroy(self, request, *args, **kwargs):
        review = self.get_object()
        review.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # POST /api/v1/reviews/{id}/respond/
    @action(detail=True, methods=["post"])
    def respond(self, request, pk=None):
        review = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = self.service.respond(
            review=review,
            actor=request.user,
            response_text=serializer.validated_data["landlord_response"],
        )
        return Response(ReviewSerializer(review).data)

    # PATCH /api/v1/reviews/{id}/status/
    @action(detail=True, methods=["patch"], url_path="status")
    def update_status(self, request, pk=None):
        review = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = self.service.update_status(
            review=review, new_status=serializer.validated_data["status"]
        )
        return Response(ReviewSerializer(review).data)

    # GET /api/v1/reviews/mine/
    @action(detail=False, methods=["get"])
    def mine(self, request):
        queryset = self.service.list_mine(request.user)
        return Response(ReviewSerializer(queryset, many=True).data)

    # GET /api/v1/reviews/landlord/
    @action(detail=False, methods=["get"])
    def landlord(self, request):
        queryset = self.service.list_for_landlord(request.user)
        return Response(ReviewSerializer(queryset, many=True).data)
