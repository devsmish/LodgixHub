from rest_framework.permissions import BasePermission

from apps.security.constants import (
    GROUP_ADMIN,
    GROUP_LANDLORD,
    GROUP_MODERATOR,
    GROUP_TENANT,
)


class IsTenant(BasePermission):
    """Allows access only to users from the 'tenant' group."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.groups.filter(name=GROUP_TENANT).exists()
        )


class IsLandlord(BasePermission):
    """
    Allows access only to users belonging to the system group 'landlord'.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.groups.filter(name=GROUP_LANDLORD).exists()
        )


class IsModerator(BasePermission):
    """Allows access only to users in the 'moderator' group (Moderators)."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.groups.filter(name=GROUP_MODERATOR).exists()
        )


class IsAdmin(BasePermission):
    """Allows access to users in the 'admin' group or Django superusers."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                request.user.is_superuser
                or request.user.groups.filter(name=GROUP_ADMIN).exists()
            )
        )


class IsOwner(BasePermission):
    """
    Grants access only to the object's direct owner.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, "user"):
            return obj.user == request.user

        if hasattr(obj, "owner"):
            return obj.owner == request.user

        return False
