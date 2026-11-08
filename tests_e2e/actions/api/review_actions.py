from __future__ import annotations

from tests_e2e.actions.api.base_api_action import BaseAPIAction
from tests_e2e.actions.base import ActionResult, ReviewActions


class APIReviewActions(BaseAPIAction, ReviewActions):
    """See apps/reviews/controller/review_controller.py — payload."""

    def create(self, *, booking_id: str, rating: int, comment: str = "") -> ActionResult:
        return self._post("/reviews/", {"booking_id": booking_id, "rating": rating, "comment": comment})

    def get(self, review_id: str) -> ActionResult:
        return self._get(f"/reviews/{review_id}/")

    def update(self, review_id: str, *, rating: int | None = None, comment: str | None = None) -> ActionResult:
        body = {}
        if rating is not None:
            body["rating"] = rating
        if comment is not None:
            body["comment"] = comment
        return self._patch(f"/reviews/{review_id}/", body)

    def delete(self, review_id: str) -> ActionResult:
        return self._delete(f"/reviews/{review_id}/")

    def respond(self, review_id: str, *, response_text: str) -> ActionResult:
        return self._post(f"/reviews/{review_id}/respond/", {"landlord_response": response_text})

    def update_status(self, review_id: str, *, status: str) -> ActionResult:
        return self._patch(f"/reviews/{review_id}/status/", {"status": status})

    def list_for_listing(self, listing_id: str) -> ActionResult:
        return self._get("/reviews/", params={"listing_id": listing_id})

    def list_moderation_queue(self) -> ActionResult:
        return self._get("/reviews/")

    def mine(self) -> ActionResult:
        return self._get("/reviews/mine/")

    def for_landlord(self) -> ActionResult:
        return self._get("/reviews/landlord/")
