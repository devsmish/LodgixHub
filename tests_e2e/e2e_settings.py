"""
Settings for the test suite itself (not to be confused with Django’s `config.settings`).

`TEST_MODE` toggles the transport mechanism used by "Actions" fixtures:
  - "api" (default) — pure HTTP via the Playwright `APIRequestContext`, without a browser.
    It acts as a "black box" interacting with a live, running Django server (provided by
    `pytest-django`’s `live_server`).
  - "ui" — reserved for future use, once a frontend is implemented. Implementations in
    `actions/ui/*.py` must adhere to the same interface (defined in `actions/base.py`) as
    those in `actions/api/*.py`. This ensures that tests in `tests/*.py` remain unchanged;
    only the Actions factory injected in `conftest.py` needs to be swapped.

This is controlled via an environment variable rather than a hardcoded constant, allowing the
same test suite to be run in a CI environment in either mode without requiring any file
modifications.

    E2E_TEST_MODE=ui pytest tests_e2e/
"""

import os

TEST_MODE = os.environ.get("E2E_TEST_MODE", "api")

# If TEST_MODE="api" and BASE_URL is not explicitly set, the `live_server` fixture from
# `pytest-django` is used (a real Django development server, spun up for the duration of
# the test session). If E2E_BASE_URL is explicitly set, you can run this same suite as a
# black-box test against a staging or production environment, without touching the
# project's test database at all.
BASE_URL = os.environ.get("E2E_BASE_URL")

API_PREFIX = "/api/v1"

DEFAULT_TIMEOUT_MS = 10_000
