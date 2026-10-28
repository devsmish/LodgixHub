"""
A shared transport layer for all `actions/api/*.py` files.

One `APIRequestContext` per actor (user) per test — Playwright automatically
manages cookies (including the `httponly` `refresh_token` set by `/auth/login/`
and `/auth/register/`) within a single context. Consequently, the login process
and subsequent requests from the same actor function as a single browser session,
eliminating the need to manually pass cookies between calls.

The bearer (access) token is stored in the same location and manually injected
into the header, as, by design, the access token is never placed in a cookie
(see apps/security/controller.py).

All actual Playwright calls (creating a context, GET/POST requests, disposal,
etc.) are proxied through `PlaywrightThread.run(...)` — see `playwright_thread.py`:
The Playwright synchronous API must reside in a single, dedicated thread—separate
from Django/pytest-django—otherwise, access to the database will break.

"""
from __future__ import annotations

from typing import Any

from tests_e2e.actions.api.playwright_thread import PlaywrightThread
from tests_e2e.actions.base import ActionResult
from tests_e2e.e2e_settings import API_PREFIX


class BaseAPIAction:
    def __init__(self, request_context, session: "ActorSession", pw_thread: PlaywrightThread):
        self._ctx = request_context
        self._session = session
        self._pw = pw_thread

    def _url(self, path: str) -> str:
        path = path if path.startswith("/") else f"/{path}"
        return f"{API_PREFIX}{path}"

    def _headers(self, extra: dict | None = None) -> dict:
        headers = {}
        if self._session.access_token:
            headers["Authorization"] = f"Bearer {self._session.access_token}"
        if extra:
            headers.update(extra)
        return headers

    def _to_result(self, response) -> ActionResult:
        try:
            data = response.json()
        except Exception:
            data = response.text()
        return ActionResult(ok=response.ok, status=response.status, data=data, raw=response)

    def _dispatch(self, fn) -> ActionResult:
        """It performs an HTTP call and parses the response body in a single step
        within a Playwright thread. Since `APIResponse` reads the body lazily—using
        the same internal dispatcher as the request itself—calling `.json()` or
        `.text()` *after* exiting `PlaywrightThread.run(...)` causes Playwright to
        crash with a `greenlet.error: Cannot switch to a different thread`. This
        happens because the greenlet that handled the original call is no longer
        active. For this reason, the `status`, `ok`, and `data` values are collected
        into an `ActionResult` directly within the same lambda function that executes
        the request."""

        def _run():
            response = fn()
            return self._to_result(response)

        return self._pw.run(_run)

    def _get(self, path: str, params: dict | None = None) -> ActionResult:
        headers = self._headers()
        return self._dispatch(lambda: self._ctx.get(self._url(path), params=params, headers=headers))

    def _post(self, path: str, json_body: dict | None = None) -> ActionResult:
        headers = self._headers()
        return self._dispatch(lambda: self._ctx.post(self._url(path), data=json_body, headers=headers))

    def _post_multipart(self, path: str, multipart: dict) -> ActionResult:
        """For file uploads (Photo), Playwright automatically sets the `multipart/form-data`
        and `boundary` parameters. Do not manually modify the `Content-Type` header, as
        doing so will cause it—along with the `boundary`—to be lost."""
        headers = self._headers()
        return self._dispatch(lambda: self._ctx.post(self._url(path), multipart=multipart, headers=headers))

    def _patch(self, path: str, json_body: dict | None = None) -> ActionResult:
        headers = self._headers()
        return self._dispatch(lambda: self._ctx.patch(self._url(path), data=json_body, headers=headers))

    def _delete(self, path: str) -> ActionResult:
        headers = self._headers()
        return self._dispatch(lambda: self._ctx.delete(self._url(path), headers=headers))


class ActorSession:
    """Holds the access token for the current actor. A single `ActorSession` per "user"
    in a test is shared across all `*Action` objects for that actor; this ensures that
    an `auth.login(...)` call in one class is immediately visible to a `booking.create(...)`
    call in another, without the need to manually pass the token throughout the test."""

    def __init__(self):
        self.access_token: str | None = None
        self.user_id: str | None = None
        self.email: str | None = None

    def set_from_auth_response(self, data: dict) -> None:
        self.access_token = data.get("access")
        self.user_id = data.get("user_id")
        self.email = data.get("email")

    def clear(self) -> None:
        self.access_token = None
        self.user_id = None
        self.email = None
