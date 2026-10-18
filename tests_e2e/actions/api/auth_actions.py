from __future__ import annotations

from tests_e2e.actions.api.base_api_action import BaseAPIAction
from tests_e2e.actions.base import ActionResult, AuthActions


class APIAuthActions(BaseAPIAction, AuthActions):
    """POST /auth/register/, /auth/login/, /auth/logout/.

    See apps/security/dto/register.py and apps/security/controller.py —
    the payload and response structure are copied from them verbatim,
    ensuring that this class breaks if the endpoint contract changes
    (rather than silently drifting out of sync with reality).
    """

    def register(
        self,
        *,
        email: str,
        password: str,
        role: str,
        first_name: str = "",
        last_name: str = "",
        terms_accepted: bool = True,
    ) -> ActionResult:
        result = self._post(
            "/auth/register/",
            {
                "email": email,
                "password": password,
                "password_confirm": password,
                "first_name": first_name,
                "last_name": last_name,
                "role": role,
                "terms_accepted": terms_accepted,
            },
        )
        if result.ok and isinstance(result.data, dict):
            self._session.set_from_auth_response(result.data)
        return result

    def login(self, *, email: str, password: str) -> ActionResult:
        result = self._post("/auth/login/", {"email": email, "password": password})
        if result.ok and isinstance(result.data, dict):
            self._session.set_from_auth_response(result.data)
        return result

    def logout(self) -> ActionResult:
        result = self._post("/auth/logout/")
        if result.ok:
            self._session.clear()
        return result
