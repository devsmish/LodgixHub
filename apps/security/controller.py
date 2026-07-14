from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.security.dto.register import RegisterResponseSerializer, RegisterSerializer
from apps.security.dto.token import CustomTokenObtainPairSerializer
from apps.security.services import mint_token_pair, register_user


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    """Common location for setting the refresh_token cookie"""
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=not settings.DEBUG,  # True in prod (HTTPS), False in local (HTTP)
        samesite="Lax",
        max_age=int(api_settings.REFRESH_TOKEN_LIFETIME.total_seconds()),
    )


class RegisterView(APIView):
    """POST /api/v1/auth/register/ — creates a User and immediately issues tokens."""

    permission_classes = [AllowAny]
    # CustomJWTAuthentication will attempt to validate the Authorization header
    # if present, and will raise an AuthenticationFailed (401) exception—before
    # permission_classes are checked—if the header contains an invalid token.
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth-register"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = register_user(**serializer.validated_data)
        refresh = mint_token_pair(user)

        response_data = RegisterResponseSerializer(
            {
                "access": str(refresh.access_token),
                "user_id": user.id,
                "email": user.email,
            }
        ).data
        response = Response(response_data, status=status.HTTP_201_CREATED)
        _set_refresh_cookie(response, str(refresh))
        return response


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth-login"

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            refresh_token = response.data.pop("refresh", None)
            if refresh_token:
                _set_refresh_cookie(response, refresh_token)
        return response


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get("refresh_token")
        response = Response(
            {"detail": "Successfully logged out."}, status=status.HTTP_200_OK
        )
        request.user.token_version += 1
        request.user.save(update_fields=["token_version", "updated_at"])

        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except TokenError:
                pass

        response.delete_cookie("refresh_token")
        return response


class TokenRefreshView(APIView):
    """
    POST /api/v1/auth/token/refresh/.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get("refresh_token")
        if not refresh_token:
            raise AuthenticationFailed("Refresh token cookie is missing.")

        try:
            refresh = RefreshToken(refresh_token)
        except TokenError as exc:
            raise AuthenticationFailed(str(exc))

        return Response({"access": str(refresh.access_token)})
