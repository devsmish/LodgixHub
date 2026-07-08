import time
from django.http import HttpRequest, HttpResponse
from rest_framework_simplejwt.tokens import TokenError, AccessToken, RefreshToken
from rest_framework_simplejwt.settings import api_settings


class JWTAuthMiddleware:
    """
    Custom middleware for automatic, seamless token renewal (Silent Refresh).

    Intercepts requests and checks the validity of the access token in the headers.
    If the token has expired but a valid refresh token exists in the HttpOnly cookies, the middleware:
      1. Generates a new access token.
      2. Injects it into the current request so that DRF successfully authorizes the user.
      3. Adds the new access token to the 'X-Access-Token' response header for the frontend.
    """

    excluded_paths = {
        "/api/v1/users/auth/login/",
        "/api/v1/users/auth/logout/",
    }

    excluded_path_prefixes = (
        "/admin/",
    )

    def __init__(self, get_response):
        self.get_response = get_response
        self.refresh_window_seconds = self._build_refresh_window_seconds()

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if self._should_skip(request):
            return self.get_response(request)

        access_token = self._get_access_token_from_header(request)
        refresh_token = request.COOKIES.get("refresh_token")

        minted_access_token: str | None = None
        should_clear_refresh_cookie = False

        if refresh_token:
            if not self._is_refresh_token_valid(refresh_token):
                should_clear_refresh_cookie = True

            elif access_token and not self._is_access_expiring(access_token):
                pass

            else:
                minted_access_token = self._mint_access_token(refresh_token)

                if minted_access_token:
                    self._set_authorization_header(request, minted_access_token)
                else:
                    should_clear_refresh_cookie = True

        response = self.get_response(request)

        if should_clear_refresh_cookie:
            response.delete_cookie("refresh_token")

        elif minted_access_token:
            response["X-Access-Token"] = minted_access_token
            response["Access-Control-Expose-Headers"] = "X-Access-Token"

        return response

    def _build_refresh_window_seconds(self) -> int:
        access_lifetime_seconds = int(api_settings.ACCESS_TOKEN_LIFETIME.total_seconds())
        return max(1, min(30, access_lifetime_seconds // 4))

    def _should_skip(self, request: HttpRequest) -> bool:
        return request.path in self.excluded_paths or request.path.startswith(self.excluded_path_prefixes)

    def _get_access_token_from_header(self, request: HttpRequest) -> str | None:
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if auth_header.startswith("Bearer "):
            try:
                return auth_header.split(" ")[1]
            except IndexError:
                return None
        return None

    def _set_authorization_header(self, request: HttpRequest, access_token: str) -> None:
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {access_token}"

    def _is_refresh_token_valid(self, refresh_token: str) -> bool:
        try:
            RefreshToken(refresh_token)
            return True
        except TokenError:
            return False
        except Exception:
            return False

    def _mint_access_token(self, refresh_token: str) -> str | None:
        try:
            refresh = RefreshToken(refresh_token)
            return str(refresh.access_token)
        except TokenError:
            return None
        except Exception:
            return None

    def _is_access_expiring(self, access_token: str) -> bool:
        try:
            token = AccessToken(access_token)
            exp_timestamp = int(token["exp"])
            now_timestamp = int(time.time())
            return exp_timestamp <= now_timestamp + self.refresh_window_seconds
        except Exception:
            return True
