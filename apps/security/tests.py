from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.test import override_settings
from django.urls import include, path, reverse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.test import APITestCase
from rest_framework.views import APIView
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from apps.security.constants import GROUP_TENANT

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
        cache.clear()  # reset ScopedRateThrottle counters between tests
        self.password = "SecretPassword123"
        self.user = User.objects.create_user(
            email="testuser@example.com",
            password=self.password,
            first_name="John",
            last_name="Doe",
        )
        self.login_url = reverse("security:login")
        self.logout_url = reverse("security:logout")
        self.register_url = reverse("security:register")
        self.refresh_url = reverse("security:token-refresh")
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

    # --- NEW: register --------------------------------------------------

    def _valid_register_payload(self, **overrides):
        payload = {
            "email": "newuser@example.com",
            "password": "S0me-Str0ng-Password!",
            "password_confirm": "S0me-Str0ng-Password!",
            "first_name": "Jane",
            "last_name": "Doe",
            "role": GROUP_TENANT,
            "terms_accepted": True,
        }
        payload.update(overrides)
        return payload

    def test_05_register_creates_user_and_returns_tokens(self):
        response = self.client.post(self.register_url, self._valid_register_payload())

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", response.data)
        self.assertIn("refresh_token", response.cookies)

        created_user = User.objects.get(email="newuser@example.com")
        self.assertTrue(created_user.groups.filter(name=GROUP_TENANT).exists())
        self.assertIsNotNone(created_user.terms_accepted_at)

    def test_06_register_password_mismatch_raises(self):
        response = self.client.post(
            self.register_url,
            self._valid_register_payload(password_confirm="different-password"),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email="newuser@example.com").exists())

    def test_07_register_weak_password_raises(self):
        """Verifies that the AUTH_PASSWORD_VALIDATORS from settings.py are actually
        applied during registration."""
        response = self.client.post(
            self.register_url,
            self._valid_register_payload(
                password="12345678", password_confirm="12345678"
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_08_register_duplicate_email_raises(self):
        response = self.client.post(
            self.register_url, self._valid_register_payload(email=self.user.email)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_09_register_without_terms_accepted_raises(self):
        response = self.client.post(
            self.register_url, self._valid_register_payload(terms_accepted=False)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_10_register_missing_role_group_surfaces_clear_error(self):
        Group.objects.filter(name=GROUP_TENANT).delete()
        with self.assertRaises(Group.DoesNotExist):
            self.client.post(self.register_url, self._valid_register_payload())

    # ------- Token refresh ----------------------------------------------

    def test_11_token_refresh_returns_new_access_token(self):
        refresh = RefreshToken.for_user(self.user)
        refresh["token_version"] = self.user.token_version
        self.client.cookies["refresh_token"] = str(refresh)

        response = self.client.post(self.refresh_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_12_token_refresh_without_cookie_raises(self):
        response = self.client.post(self.refresh_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_12b_token_refresh_ignores_stale_authorization_header(self):
        """
        Regression: missing authentication_classes = [] on TokenRefreshView
        expired access token in the `Authorization` header.
        """
        refresh = RefreshToken.for_user(self.user)
        refresh["token_version"] = self.user.token_version

        expired_access = AccessToken.for_user(self.user)
        expired_access["token_version"] = self.user.token_version
        expired_access.set_exp(lifetime=-timedelta(minutes=5))

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {expired_access}")
        self.client.cookies["refresh_token"] = str(refresh)

        response = self.client.post(self.refresh_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_13_token_refresh_with_blacklisted_token_raises(self):
        refresh = RefreshToken.for_user(self.user)
        refresh["token_version"] = self.user.token_version
        refresh.blacklist()
        self.client.cookies["refresh_token"] = str(refresh)

        response = self.client.post(self.refresh_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ------- Throttling ---------------------------------------------------

    def test_14_login_throttled_after_5_attempts_per_minute(self):
        """Brute-force protection — no more than 5 login attempts
        per minute from a single IP address."""
        for _ in range(5):
            response = self.client.post(
                self.login_url, {"email": self.user.email, "password": "wrong-password"}
            )
            self.assertNotEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        response = self.client.post(
            self.login_url, {"email": self.user.email, "password": "wrong-password"}
        )
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_15_register_throttled_after_5_attempts_per_minute(self):
        """Protection against spam registrations: no more than 5 registrations
        per minute from a single IP address."""
        for i in range(5):
            response = self.client.post(
                self.register_url,
                self._valid_register_payload(email=f"throttle{i}@example.com"),
            )
            self.assertNotEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        response = self.client.post(
            self.register_url,
            self._valid_register_payload(email="throttle-overflow@example.com"),
        )
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_16_login_and_register_throttles_are_independent(self):
        for _ in range(5):
            self.client.post(
                self.login_url, {"email": self.user.email, "password": "wrong-password"}
            )

        response = self.client.post(self.register_url, self._valid_register_payload())
        self.assertNotEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
