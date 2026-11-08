from __future__ import annotations

from tests_e2e.actions.api.base_api_action import BaseAPIAction
from tests_e2e.actions.base import ActionResult, UserActions


class APIUserActions(BaseAPIAction, UserActions):
    """apps/users/controller/user_controller.py — payload/paths."""

    def me(self) -> ActionResult:
        return self._get("/users/me/")

    def update_me(self, payload: dict) -> ActionResult:
        return self._patch("/users/me/", payload)

    def delete_me(self) -> ActionResult:
        return self._delete("/users/me/")

    def get_public_profile(self, user_id: str) -> ActionResult:
        return self._get(f"/users/{user_id}/")

    def list_users(self, params: dict | None = None) -> ActionResult:
        return self._get("/users/", params=params)

    def block(self, user_id: str, *, reason: str) -> ActionResult:
        return self._post(f"/users/{user_id}/block/", {"blocked_reason": reason})

    def unblock(self, user_id: str) -> ActionResult:
        return self._post(f"/users/{user_id}/unblock/")

    def update_groups(self, user_id: str, *, groups: list[str]) -> ActionResult:
        return self._patch(f"/users/{user_id}/groups/", {"groups": groups})

    def delete_user(self, user_id: str) -> ActionResult:
        return self._delete(f"/users/{user_id}/")
