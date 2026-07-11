from rest_framework.permissions import BasePermission

from apps.security.constants import (
    GROUP_ADMIN,
    GROUP_LANDLORD,
    GROUP_MODERATOR,
    GROUP_TENANT,
)


def _get_cached_group_names(user) -> set:

    if not hasattr(user, "_cached_group_names"):
        user._cached_group_names = set(user.groups.values_list("name", flat=True))
    return user._cached_group_names


class IsTenant(BasePermission):
    """Allows access only to users from the 'tenant' group."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and GROUP_TENANT in _get_cached_group_names(request.user)
        )


class IsLandlord(BasePermission):
    """
    Allows access only to users belonging to the system group 'landlord'.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and GROUP_LANDLORD in _get_cached_group_names(request.user)
        )


class IsModerator(BasePermission):
    """Allows access only to users in the 'moderator' group (Moderators)."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and GROUP_MODERATOR in _get_cached_group_names(request.user)
        )


class IsAdmin(BasePermission):
    """Allows access to users in the 'admin' group or Django superusers."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                request.user.is_superuser
                or GROUP_ADMIN in _get_cached_group_names(request.user)
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
