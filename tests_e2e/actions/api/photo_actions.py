from __future__ import annotations

from tests_e2e.actions.api.base_api_action import BaseAPIAction
from tests_e2e.actions.base import ActionResult, PhotoActions


class APIPhotoActions(BaseAPIAction, PhotoActions):
    """POST(multipart)/GET /listings/{listing_id}/photos/, PATCH/DELETE .../{photo_id}/."""

    def upload(self, listing_id: str, *, image_bytes: bytes, filename: str = "photo.jpg", caption: str = "") -> ActionResult:
        return self._post_multipart(
            f"/listings/{listing_id}/photos/",
            {
                "image": {"name": filename, "mimeType": "image/jpeg", "buffer": image_bytes},
                "caption": caption,
            },
        )

    def update(self, listing_id: str, photo_id: str, payload: dict) -> ActionResult:
        return self._patch(f"/listings/{listing_id}/photos/{photo_id}/", payload)

    def delete(self, listing_id: str, photo_id: str) -> ActionResult:
        return self._delete(f"/listings/{listing_id}/photos/{photo_id}/")

    def list_for_listing(self, listing_id: str) -> ActionResult:
        return self._get(f"/listings/{listing_id}/photos/")
