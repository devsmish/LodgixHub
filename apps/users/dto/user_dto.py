from django.contrib.auth.models import Group
from rest_framework import serializers

from apps.users.choices import BlockedReason
from apps.users.models.user import User


class UserMeSerializer(serializers.ModelSerializer):
    """GET/PATCH /api/v1/users/me/ — own user profile.
    Email and roles (groups) cannot be edited via this serializer."""

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "nickname",
            "birth_date",
            "gender",
            "phone",
            "contact_phone",
            "avatar",
            "notify_by_email",
            "date_joined",
        )
        read_only_fields = ("id", "email", "date_joined")


class UserPublicSerializer(serializers.ModelSerializer):
    """GET /api/v1/users/{id}/ — limited public profile."""

    class Meta:
        model = User
        fields = ("id", "nickname", "avatar", "contact_phone")


class UserAdminListSerializer(serializers.ModelSerializer):
    """GET /api/v1/users/ — list for the moderator/admin."""

    groups = serializers.SlugRelatedField(
        many=True, slug_field="name", queryset=Group.objects.all(), required=False
    )

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "nickname",
            "is_active",
            "is_staff",
            "blocked_at",
            "blocked_reason",
            "groups",
            "date_joined",
        )
        read_only_fields = fields


class BlockUserSerializer(serializers.Serializer):
    """POST /api/v1/users/{id}/block/ — a reason is mandatory
    and must be selected strictly from the reference list."""

    blocked_reason = serializers.ChoiceField(choices=BlockedReason.choices)


class GroupsUpdateSerializer(serializers.Serializer):
    """PATCH /api/v1/users/{id}/groups/ — complete replacement of the set of roles."""

    groups = serializers.SlugRelatedField(
        many=True, slug_field="name", queryset=Group.objects.all()
    )
