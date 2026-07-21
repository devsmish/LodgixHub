from rest_framework import serializers


class LogoutResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


class TokenRefreshResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
