"""
The Playwright sync API maintains a "running" asyncio event loop in the thread where
`sync_playwright()` was called for the entire lifetime of the object—not just at startup.
If this happens to be the same thread that `pytest-django` uses to access the Django ORM
(typically the main `pytest` thread), Django’s `async_unsafe` guard—which checks for an
active loop via `asyncio.get_running_loop()`—mistakenly identifies the environment as an
asynchronous context. Consequently, it blocks *all* database access (triggering a
`SynchronousOnlyOperation` error). This issue persists beyond the initial call, affecting
every subsequent use of `django_db` or `live_server` for the remainder of the test session.

The only clean solution is to avoid running Playwright in the main thread altogether.
`PlaywrightThread` is a single-threaded worker (`ThreadPoolExecutor(max_workers=1)`)
that houses the entirety of Playwright—including `sync_playwright()`, all
`APIRequestContext` instances, and every HTTP call. The main thread (where
Django/pytest resides) never interacts with Playwright’s internal `asyncio` state, allowing
it to continue accessing the database without any issues.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Callable, TypeVar

from playwright.sync_api import Playwright, sync_playwright

T = TypeVar("T")


class PlaywrightThread:
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="playwright-e2e")
        self._context_manager = None
        self.playwright: Playwright | None = None

    def start(self) -> None:
        def _start():
            self._context_manager = sync_playwright()
            self.playwright = self._context_manager.__enter__()

        self._executor.submit(_start).result()

    def stop(self) -> None:
        def _stop():
            if self._context_manager is not None:
                self._context_manager.__exit__(None, None, None)

        self._executor.submit(_stop).result()
        self._executor.shutdown(wait=True)

    def run(self, fn: Callable[[], T]) -> T:
        """Execute an arbitrary call within a Playwright thread and await the
        result. All interactions with `APIRequestContext`/`APIResponse` must
        go through this method—raw Playwright objects are not thread-safe when
        accessed from a different thread."""
        return self._executor.submit(fn).result()
