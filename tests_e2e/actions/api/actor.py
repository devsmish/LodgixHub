"""
APIActor represents a single "user" in a test: it consists of one
APIRequestContext (representing one HTTP/cookie session) and one
ActorSession (representing one access token), with various *Actions—such
as `actor.auth`, `actor.listings`, `actor.bookings`, and so on—layered
on top, all of which the test can access.

This serves as an extension point for switching to the UI layer
(`E2E_TEST_MODE=ui`): instead of `APIActor`, the fixture in `conftest.py`
will provide a `UIActor`. While it retains the same attribute names
(`.auth`, `.listings`, `.bookings`), its internal implementation—located
in `actions/ui/*.py`—uses Playwright’s `Page` object rather than HTTP
requests. Tests that interact solely via `actor.<domain>.<method>(...)`
will remain unaffected.
"""
from __future__ import annotations

from tests_e2e.actions.api.base_api_action import ActorSession
from tests_e2e.actions.api.auth_actions import APIAuthActions
from tests_e2e.actions.api.booking_actions import APIBookingActions
from tests_e2e.actions.api.dispute_actions import APIDisputeActions
from tests_e2e.actions.api.listing_actions import APIListingActions
from tests_e2e.actions.api.photo_actions import APIPhotoActions
from tests_e2e.actions.api.playwright_thread import PlaywrightThread
from tests_e2e.actions.api.room_actions import APIRoomActions


class APIActor:
    def __init__(self, request_context, pw_thread: PlaywrightThread):
        self.session = ActorSession()
        self.auth = APIAuthActions(request_context, self.session, pw_thread)
        self.listings = APIListingActions(request_context, self.session, pw_thread)
        self.rooms = APIRoomActions(request_context, self.session, pw_thread)
        self.photos = APIPhotoActions(request_context, self.session, pw_thread)
        self.bookings = APIBookingActions(request_context, self.session, pw_thread)
        self.disputes = APIDisputeActions(request_context, self.session, pw_thread)

def use_token(self, access_token: str) -> None:
        """Injecting an existing access token directly (bypassing `/auth/login/`) —
        used for roles that cannot be created via public registration (e.g.,
        moderator/admin); see `fixtures/users.py`."""
        self.session.access_token = access_token
