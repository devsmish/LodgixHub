from django.contrib.auth.models import Group
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.security.permissions import IsAdmin, IsModerator
from apps.users.dto import (
    BlockUserSerializer,
    GroupsUpdateSerializer,
    UserAdminListSerializer,
    UserMeSerializer,
    UserPublicSerializer,
)
from apps.users.paginations import UserPagination
from apps.users.repositories import UserRepository
from apps.users.services import UserService


class GroupListView(mixins.ListModelMixin, viewsets.GenericViewSet):
    """GET /api/v1/roles/ — list of available roles."""

    queryset = Group.objects.all()
    permission_classes = [IsAdmin]

    @extend_schema(
        responses={
            200: OpenApiResponse(
                response={"type": "array", "items": {"type": "string"}}
            )
        }
    )
    def list(self, request, *args, **kwargs):
        names = list(self.get_queryset().values_list("name", flat=True))
        return Response(names)


class UserViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):

    repository = UserRepository()
    service = UserService()
    pagination_class = UserPagination
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.repository.get_all_queryset()

    def get_permissions(self):
        if self.action == "list":
            return [(IsModerator | IsAdmin)()]
        if self.action in ("block", "unblock", "update_groups", "destroy"):
            return [IsAdmin()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return UserPublicSerializer
        return UserAdminListSerializer

    # GET /api/v1/users/ — list, moderator/admin
    def list(self, request, *args, **kwargs):
        queryset = self.service.list_users(request.query_params)
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(
            page if page is not None else queryset, many=True
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    # GET /api/v1/users/{id}/ — public profile
    def retrieve(self, request, *args, **kwargs):
        target = self.service.get_public_profile(request.user, kwargs["pk"])
        if target is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(target)
        return Response(serializer.data)

    # GET / PATCH / DELETE /api/v1/users/me/
    @action(detail=False, methods=["get", "patch", "delete"])
    def me(self, request):
        if request.method == "GET":
            return Response(UserMeSerializer(request.user).data)

        if request.method == "PATCH":
            serializer = UserMeSerializer(request.user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            user = self.service.update_me(request.user, serializer.validated_data)
            return Response(UserMeSerializer(user).data)

        # DELETE
        self.service.delete_self(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # POST /api/v1/users/{id}/block/
    @action(detail=True, methods=["post"])
    def block(self, request, pk=None):
        serializer = BlockUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target = self.repository.get_by_id_any(pk)
        if target is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        self.service.block(
            target,
            blocked_reason=serializer.validated_data["blocked_reason"],
            blocked_by=request.user,
        )
        return Response(UserAdminListSerializer(target).data)

    # POST /api/v1/users/{id}/unblock/
    @action(detail=True, methods=["post"])
    def unblock(self, request, pk=None):
        target = self.repository.get_by_id_any(pk)
        if target is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        self.service.unblock(target)
        return Response(UserAdminListSerializer(target).data)

    # PATCH /api/v1/users/{id}/groups/
    @action(detail=True, methods=["patch"], url_path="groups")
    def update_groups(self, request, pk=None):
        serializer = GroupsUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target = self.repository.get_by_id_any(pk)
        if target is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        self.service.update_groups(target, serializer.validated_data["groups"])
        return Response(UserAdminListSerializer(target).data)

    # DELETE /api/v1/users/{id}/
    def destroy(self, request, *args, **kwargs):
        target = self.repository.get_by_id_any(kwargs["pk"])
        if target is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        self.service.delete_by_admin(target)
        return Response(status=status.HTTP_204_NO_CONTENT)
