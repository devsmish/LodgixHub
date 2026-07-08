from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed


class CustomJWTAuthentication(JWTAuthentication):
    """
    A custom authentication class for DRF.

    In addition to the standard verification of the JWT signature and expiration, this layer extracts
    the 'token_version' from the token payload and compares it against the current value in the database.
    If an admin changes the version in the database (or a user changes their password), the token
    is instantly invalidated across all devices.
    """

    def get_user(self, validated_token):
        user = super().get_user(validated_token)

        token_version_in_jwt = validated_token.get('token_version')

        if token_version_in_jwt is None or user.token_version != token_version_in_jwt:
            raise AuthenticationFailed(
                detail="The session has expired or was revoked. Please log in again.",
                code="token_revoked"
            )

        return user
