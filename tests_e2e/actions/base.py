"""
Business-action-level contracts are analogous to the "Page Object" pattern
in the classic POM (Page Object Model) approach, with the difference that
instead of a "page," the focus is on a "resource" or "use case" (e.g., Auth,
Listing, Booking, etc.).

The concept is that tests located in `tests_e2e/tests/*.py` never interact
directly with HTTP or Playwright. Instead, they invoke methods—such as
`auth.register(...)` or `bookings.create(...)`—which are defined here as
an abstract contract.

Currently, the only implementation is located in `actions/api/*.py` (pure
HTTP via the Playwright `APIRequestContext`). Once the frontend is introduced,
implementations with the same method names and signatures will be added to
`actions/ui/*.py`; internally, however, these will perform actions by clicking
on page elements via the Playwright `Page` object, rather than making HTTP
requests. The tests themselves will not need to be modified—the only change
required will be which implementation the factory in `conftest.py` provides
(see `E2E_TEST_MODE`).

`Namedtuple`/`dataclass` results (`ActionResult`) are used instead of a plain
`dict` to ensure that the structure of the returned value remains consistent
across both API and UI implementations—even though the underlying mechanism
for determining the status differs fundamentally (e.g., an HTTP status code
for the API versus the visibility of an error element in the UI). The fields
`status` and `ok` form a shared, minimal contract, while `data` and `raw` are
implementation-specific and are not guaranteed to be present in the UI.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ActionResult:
    """A unified wrapper for action results, independent of the transport layer.

    ok — whether the action was successful from a business logic perspective
         (for APIs: 2xx; for UI: e.g., "form submitted without errors")
    status — HTTP status, if applicable (only for API implementations; None for UI)
    data — the parsed response body (API) / data extracted from the page (UI)
    raw — the original transport object (Playwright APIResponse / Page) —
          used only within Action classes and for rare edge-case
          test assertions; in general, tests should rely on data/status.
    """

    ok: bool
    status: int | None
    data: Any
    raw: Any = field(default=None, repr=False)


class AuthActions(ABC):
    @abstractmethod
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
        """New user registration. Upon success, the action implementation
        itself must store the access token for subsequent calls made on
        behalf of this user (the session/context is bound to a single
        actor)."""

    @abstractmethod
    def login(self, *, email: str, password: str) -> ActionResult:
        ...

    @abstractmethod
    def logout(self) -> ActionResult:
        ...


class ListingActions(ABC):
    @abstractmethod
    def create(self, payload: dict) -> ActionResult:
        """Creates an ad on behalf of the current actor (always in 'draft' status)."""

    @abstractmethod
    def publish(self, listing_id: str) -> ActionResult:
        """draft -> published, accessible only to the owner."""

    @abstractmethod
    def get(self, listing_id: str) -> ActionResult:
        ...


class RoomActions(ABC):
    @abstractmethod
    def create(self, listing_id: str, payload: dict) -> ActionResult:
        ...

    @abstractmethod
    def list_for_listing(self, listing_id: str) -> ActionResult:
        ...


class PhotoActions(ABC):
    @abstractmethod
    def upload(self, listing_id: str, *, image_bytes: bytes, filename: str = "photo.jpg", caption: str = "") -> ActionResult:
        """POST /listings/{listing_id}/photos/ — multipart."""

    @abstractmethod
    def list_for_listing(self, listing_id: str) -> ActionResult:
        ...


class BookingActions(ABC):
    @abstractmethod
    def create(self, payload: dict) -> ActionResult:
        ...

    @abstractmethod
    def get(self, booking_id: str) -> ActionResult:
        ...

    @abstractmethod
    def list(self) -> ActionResult:
        ...

    @abstractmethod
    def confirm(self, booking_id: str) -> ActionResult:
        ...

    @abstractmethod
    def reject(self, booking_id: str) -> ActionResult:
        ...

    @abstractmethod
    def cancel(self, booking_id: str, *, cancellation_reason_id: str | None = None) -> ActionResult:
        ...


class DisputeActions(ABC):
    @abstractmethod
    def open(self, booking_id: str, *, reason_category: str, reason: str, claim_amount: str = "0.00") -> ActionResult:
        """POST /bookings/{booking_id}/disputes/ — open a dispute regarding a booking."""

    @abstractmethod
    def list_for_booking(self, booking_id: str) -> ActionResult:
        """GET /bookings/{booking_id}/disputes/ — all disputes regarding a specific booking."""

    @abstractmethod
    def get(self, dispute_id: str) -> ActionResult:
        ...

    @abstractmethod
    def list(self, *, status: str | None = None) -> ActionResult:
        """GET /disputes/ — moderation queue (moderator/admin) or one's own disputes."""

    @abstractmethod
    def review(self, dispute_id: str) -> ActionResult:
        """PATCH /disputes/{id}/review/ — open -> under_review, moderator/admin."""

    @abstractmethod
    def resolve(
        self,
        dispute_id: str,
        *,
        status: str,
        resolution_favor: str,
        resolution_amount: str | None = None,
        notes: str = "",
    ) -> ActionResult:
        """POST /disputes/{id}/resolve/ — under_review -> resolved_*, moderator/admin."""

    @abstractmethod
    def add_evidence(self, dispute_id: str, *, url: str, description: str = "") -> ActionResult:
        ...

    @abstractmethod
    def list_evidence(self, dispute_id: str) -> ActionResult:
        ...

    @abstractmethod
    def delete_evidence(self, dispute_id: str, evidence_id: str) -> ActionResult:
        ...
