from __future__ import annotations

from tests_e2e.actions.api.base_api_action import BaseAPIAction
from tests_e2e.actions.base import ActionResult, AmenityActions


class APIAmenityActions(BaseAPIAction, AmenityActions):
    """POST/GET /amenities/."""

    def create(self, *, name: str, slug: str, icon: str = "") -> ActionResult:
        return self._post("/amenities/", {"name": name, "slug": slug, "icon": icon})

    def list(self) -> ActionResult:
        return self._get("/amenities/")
