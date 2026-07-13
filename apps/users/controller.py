from django.contrib.auth.models import Group
from rest_framework import generics, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from apps.users.models import User


class GroupListView(generics.ListAPIView):

    queryset = Group.objects.all()
    permission_classes = [IsAuthenticated]


class UserViewSet(viewsets.GenericViewSet):

    queryset = User.objects.all()
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get", "patch", "delete"])
    def me(self, request):
        raise NotImplementedError

    @action(detail=True, methods=["post"])
    def block(self, request, pk=None):
        raise NotImplementedError

    @action(detail=True, methods=["post"])
    def unblock(self, request, pk=None):
        raise NotImplementedError

    @action(detail=True, methods=["patch"])
    def groups(self, request, pk=None):
        raise NotImplementedError

    def destroy(self, request, *args, **kwargs):
        raise NotImplementedError
