from __future__ import annotations

from tests_e2e.actions.api.base_api_action import BaseAPIAction
from tests_e2e.actions.base import ActionResult, BookingActions


class APIBookingActions(BaseAPIAction, BookingActions):
    """POST/GET /bookings/, /{id}/confirm/, /{id}/reject/, /{id}/cancel/.

    See apps/bookings/dto/booking_dto.py — BookingCreateSerializer requires
    exactly one of listing_id or room_id, both dates, and guests_count.
    Validation is intentionally not duplicated here; this class simply
    passes on whatever the test provides—ensuring the correctness (or
    incorrectness) of the payload is the test's responsibility.
    """

    def create(self, payload: dict) -> ActionResult:
        return self._post("/bookings/", payload)

    def get(self, booking_id: str) -> ActionResult:
        return self._get(f"/bookings/{booking_id}/")

    def list(self) -> ActionResult:
        return self._get("/bookings/")

    def confirm(self, booking_id: str) -> ActionResult:
        return self._post(f"/bookings/{booking_id}/confirm/")

    def reject(self, booking_id: str) -> ActionResult:
        return self._post(f"/bookings/{booking_id}/reject/")

    def cancel(self, booking_id: str, *, cancellation_reason_id: str | None = None) -> ActionResult:
        body = {}
        if cancellation_reason_id:
            body["cancellation_reason_id"] = cancellation_reason_id
        return self._post(f"/bookings/{booking_id}/cancel/", body)
