from __future__ import annotations

from tests_e2e.actions.api.base_api_action import BaseAPIAction
from tests_e2e.actions.base import ActionResult, PhotoActions


class APIPhotoActions(BaseAPIAction, PhotoActions):
    """POST (multipart)/GET /listings/{listing_id}/photos/."""

    def upload(self, listing_id: str, *, image_bytes: bytes, filename: str = "photo.jpg", caption: str = "") -> ActionResult:
        return self._post_multipart(
            f"/listings/{listing_id}/photos/",
            {
                "image": {"name": filename, "mimeType": "image/jpeg", "buffer": image_bytes},
                "caption": caption,
            },
        )

    def list_for_listing(self, listing_id: str) -> ActionResult:
        return self._get(f"/listings/{listing_id}/photos/")
