from __future__ import annotations

from tests_e2e.actions.api.base_api_action import BaseAPIAction
from tests_e2e.actions.base import ActionResult, CancellationReasonActions


class APICancellationReasonActions(BaseAPIAction, CancellationReasonActions):
    """POST/GET /cancellation-reasons/. Unlike Amenity, the GET method
    requires authorization (IsAuthenticated) rather than AllowAny — see
    apps/bookings/controller/cancellation_reason_controller.py."""

    def create(self, *, code: str, description: str) -> ActionResult:
        return self._post("/cancellation-reasons/", {"code": code, "description": description})

    def list(self) -> ActionResult:
        return self._get("/cancellation-reasons/")
