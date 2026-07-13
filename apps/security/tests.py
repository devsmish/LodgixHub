from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import include, path, reverse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.test import APITestCase
from rest_framework.views import APIView
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

User = get_user_model()


# Creating a mock protected endpoint for isolated middleware testing.
class DummyProtectedView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return Response({"detail": "Access granted"}, status=status.HTTP_200_OK)


# Creating a test URL map
urlpatterns = [
    path("api/v1/", include("apps.security.urls", namespace="security")),
    path("api/v1/test-protected/", DummyProtectedView.as_view(), name="test-protected"),
]


# Overriding the root URL configuration for this test class
@override_settings(ROOT_URLCONF="apps.security.tests")
class JWTAuthenticationAndMiddlewareTestCase(APITestCase):

    def setUp(self):
        self.password = "SecretPassword123"
        self.user = User.objects.create_user(
            email="testuser@example.com",
            password=self.password,
            first_name="John",
            last_name="Doe",
        )
        self.login_url = reverse("security:login")
        self.logout_url = reverse("security:logout")
        self.protected_url = reverse("test-protected")

    def test_01_login_sets_cookie_and_returns_access_token(self):
        """
        Verify that Login returns the access token in the JSON response and the refresh token in a cookie.
        """
        response = self.client.post(
            self.login_url, {"email": self.user.email, "password": self.password}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertNotIn("refresh", response.data)

        self.assertIn("refresh_token", response.cookies)
        refresh_cookie = response.cookies["refresh_token"]
        self.assertTrue(refresh_cookie["httponly"])
        self.assertEqual(refresh_cookie["samesite"], "Lax")

    def test_02_token_version_revocation(self):
        """Verification that changing `token_version` in the DB instantly revokes the token."""
        refresh = RefreshToken.for_user(self.user)
        refresh["token_version"] = self.user.token_version
        access_token = str(refresh.access_token)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        response = self.client.post(self.protected_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.token_version += 1
        self.user.save()

        response = self.client.post(self.protected_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["code"], "token_revoked")

    def test_03_middleware_silent_refresh(self):
        """Check that the middleware rotates the token if access has expired but the refresh cookie is still valid."""
        refresh = RefreshToken.for_user(self.user)
        refresh["token_version"] = self.user.token_version

        # Creating an expired access token
        expired_access = AccessToken.for_user(self.user)
        expired_access["token_version"] = self.user.token_version
        expired_access.set_exp(lifetime=-timedelta(minutes=5))

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {expired_access}")
        self.client.cookies["refresh_token"] = str(refresh)

        response = self.client.post(self.protected_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # The middleware must return a new access token in the response headers
        self.assertIn("X-Access-Token", response.headers)
        new_access_token = response.headers["X-Access-Token"]
        self.assertNotEqual(new_access_token, str(expired_access))

    def test_04_logout_clears_cookie_and_blacklists_token(self):
        """Verification that logout deletes the cookie and blacklists the refresh token."""
        refresh = RefreshToken.for_user(self.user)
        refresh["token_version"] = self.user.token_version

        self.client.cookies["refresh_token"] = str(refresh)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # The cookie must be deleted
        self.assertEqual(response.cookies["refresh_token"].value, "")

        # The token must be blacklisted
        jti = refresh["jti"]
        self.assertTrue(BlacklistedToken.objects.filter(token__jti=jti).exists())
