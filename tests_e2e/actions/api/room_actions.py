from __future__ import annotations

from tests_e2e.actions.api.base_api_action import BaseAPIAction
from tests_e2e.actions.base import ActionResult, RoomActions


class APIRoomActions(BaseAPIAction, RoomActions):
    """POST/GET /listings/{listing_id}/rooms/, PATCH/DELETE .../{room_id}/."""

    def create(self, listing_id: str, payload: dict) -> ActionResult:
        return self._post(f"/listings/{listing_id}/rooms/", payload)

    def update(self, listing_id: str, room_id: str, payload: dict) -> ActionResult:
        return self._patch(f"/listings/{listing_id}/rooms/{room_id}/", payload)

    def delete(self, listing_id: str, room_id: str) -> ActionResult:
        return self._delete(f"/listings/{listing_id}/rooms/{room_id}/")

    def list_for_listing(self, listing_id: str) -> ActionResult:
        return self._get(f"/listings/{listing_id}/rooms/")
