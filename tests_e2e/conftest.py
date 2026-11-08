"""
The root `conftest` for the `tests_e2e` test suite.

Two key architectural decisions are established here:

1. The Playwright sync API runs in a separate, dedicated thread (`PlaywrightThread`;
see `actions/api/playwright_thread.py`) rather than in the main `pytest` thread.
Otherwise, Django’s `async-safety` guard would incorrectly block all database access
for the entire session (triggering a `SynchronousOnlyOperation` error). This is a
confirmed incompatibility between the Playwright sync API and `pytest-django` when
they operate within the same thread.

2. Each actor (tenant, landlord, moderator, admin, etc.) has their own
`APIRequestContext`—and, consequently, their own cookie jar. This is important because
the `refresh_token` is set as an `HttpOnly` cookie (see `apps/security/controller.py`)
rather than being returned in the response body; if two actors in the same test were
to share a single context, a second `login()` call would overwrite the first actor’s
cookie.

The live server—provided by the `live_server` fixture in `pytest-django`—spins up an
actual Django development server in a separate thread, backed by a real test database.
Instead of emulating views in memory, the actions perform actual network requests to
`127.0.0.1:<port>`.
"""
from __future__ import annotations

import pytest

from tests_e2e import e2e_settings
from tests_e2e.actions.api.actor import APIActor
from tests_e2e.actions.api.playwright_thread import PlaywrightThread

pytest_plugins = ["tests_e2e.fixtures.users"]


@pytest.fixture(scope="session", autouse=True)
def _relax_auth_throttling():
    """In production, the `/auth/register/` and `/auth/login/` endpoints are
    rate-limited to 5 requests per minute per IP (see `config/settings.py`,
    `REST_FRAMEWORK.DEFAULT_THROTTLE_RATES`) — a proper safeguard against
    brute-force attacks and registration spam. However, this test suite
    intentionally hits the actual `/auth/register/` endpoint for every
    tenant/landlord fixture (treating it as a "black box" rather than
    bypassing the API to create users). Consequently, when running the tests
    from `localhost`, it is easy to hit this limit after only a dozen or so
    tests. To address this, we increase the limit specifically for the E2E
    session using `override_settings`, while leaving the production limit
    itself unchanged.

    IMPORTANT:
    We copy the existing `REST_FRAMEWORK` and patch only `DEFAULT_THROTTLE_RATES`,
    rather than substituting a new dictionary from scratch. Doing the latter would
    cause the JWT token to no longer be recognized, resulting in any authorized
    request failing with a 403 error: "Authentication credentials were not provided".
    """
    from django.conf import settings
    from django.test.utils import override_settings

    patched = dict(settings.REST_FRAMEWORK)
    patched["DEFAULT_THROTTLE_RATES"] = {
        **patched.get("DEFAULT_THROTTLE_RATES", {}),
        "auth-login": "10000/min",
        "auth-register": "10000/min",
    }

    with override_settings(REST_FRAMEWORK=patched):
        yield


@pytest.fixture(scope="session")
def pw_thread(django_db_setup):
    """Including `django_db_setup` in the dependencies enforces the
    initialization order: the test database is set up *before* Playwright
    starts in a separate thread. This isn’t strictly necessary (since the
    thread is already isolated), but it ensures that Django’s session-scoped
    `setup_databases()` never overlaps with the startup of Playwright,
    regardless of the order in which the fixtures are executed."""
    thread = PlaywrightThread()
    thread.start()
    yield thread
    thread.stop()


@pytest.fixture
def service_base_url(live_server):
    """If E2E_BASE_URL is explicitly set, the test suite targets an external
    environment (staging/production). Since pytest-django’s `live_server` is
    lazily instantiated—triggered only upon its first actual use—it is safe
    to include it in a function signature even when it isn’t being used.
    E2E_BASE_URL is intended for future use (e.g., running tests against a
    staging environment)."""
    return e2e_settings.BASE_URL or live_server.url


@pytest.fixture
def new_actor(pw_thread, service_base_url):
    """Factory: `new_actor()` -> `APIActor` with its own cookie jar, isolated
    from those of other actors in the test. All contexts created within the
    scope of a test are closed once the test concludes."""
    created_contexts = []

    def _make() -> APIActor:
        ctx = pw_thread.run(
            lambda: pw_thread.playwright.request.new_context(
                base_url=service_base_url, timeout=e2e_settings.DEFAULT_TIMEOUT_MS
            )
        )
        created_contexts.append(ctx)
        return APIActor(ctx, pw_thread)

    yield _make

    for ctx in created_contexts:
        pw_thread.run(ctx.dispose)
