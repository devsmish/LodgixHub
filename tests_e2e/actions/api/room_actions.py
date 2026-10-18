from __future__ import annotations

from tests_e2e.actions.api.base_api_action import BaseAPIAction
from tests_e2e.actions.base import ActionResult, RoomActions


class APIRoomActions(BaseAPIAction, RoomActions):
    """POST/GET /listings/{listing_id}/rooms/."""

    def create(self, listing_id: str, payload: dict) -> ActionResult:
        return self._post(f"/listings/{listing_id}/rooms/", payload)

    def list_for_listing(self, listing_id: str) -> ActionResult:
        return self._get(f"/listings/{listing_id}/rooms/")
