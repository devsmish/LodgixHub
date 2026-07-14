from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.security.constants import GROUP_LANDLORD, GROUP_TENANT
from apps.users.models import User


class RegisterSerializer(serializers.Serializer):

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)
    first_name = serializers.CharField(
        max_length=150, required=False, allow_blank=True, default=""
    )
    last_name = serializers.CharField(
        max_length=150, required=False, allow_blank=True, default=""
    )
    role = serializers.ChoiceField(choices=[GROUP_TENANT, GROUP_LANDLORD])
    terms_accepted = serializers.BooleanField()

    def validate_email(self, value: str) -> str:
        normalized = value.lower().strip()
        if User.all_objects.filter(email=normalized).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return normalized

    def validate_terms_accepted(self, value: bool) -> bool:
        if not value:
            raise serializers.ValidationError(
                "You must accept the terms of service to register."
            )
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        validate_password(attrs["password"])
        return attrs

    def create(self, validated_data):
        raise NotImplementedError("Use apps.security.services.register_user() instead.")


class RegisterResponseSerializer(serializers.Serializer):

    access = serializers.CharField()
    user_id = serializers.UUIDField()
    email = serializers.EmailField()
