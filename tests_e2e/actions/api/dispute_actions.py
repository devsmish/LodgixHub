from __future__ import annotations

from tests_e2e.actions.api.base_api_action import BaseAPIAction
from tests_e2e.actions.base import ActionResult, DisputeActions


class APIDisputeActions(BaseAPIAction, DisputeActions):
    """See apps/bookings/controller/dispute_controller.py and apps/bookings/dto/dispute_dto.py —
    the payloads/paths are taken from them verbatim.
    This is the most complex part of the project’s role-based access control system — it
    encompasses the widest range of visibility and moderation scenarios.
    """

    def open(self, booking_id: str, *, reason_category: str, reason: str, claim_amount: str = "0.00") -> ActionResult:
        return self._post(
            f"/bookings/{booking_id}/disputes/",
            {"reason_category": reason_category, "reason": reason, "claim_amount": claim_amount},
        )

    def list_for_booking(self, booking_id: str) -> ActionResult:
        return self._get(f"/bookings/{booking_id}/disputes/")

    def get(self, dispute_id: str) -> ActionResult:
        return self._get(f"/disputes/{dispute_id}/")

    def list(self, *, status: str | None = None) -> ActionResult:
        params = {"status": status} if status else None
        return self._get("/disputes/", params=params)

    def review(self, dispute_id: str) -> ActionResult:
        return self._patch(f"/disputes/{dispute_id}/review/")

    def resolve(
        self,
        dispute_id: str,
        *,
        status: str,
        resolution_favor: str,
        resolution_amount: str | None = None,
        notes: str = "",
    ) -> ActionResult:
        body = {"status": status, "resolution_favor": resolution_favor, "notes": notes}
        if resolution_amount is not None:
            body["resolution_amount"] = resolution_amount
        return self._post(f"/disputes/{dispute_id}/resolve/", body)

    def add_evidence(self, dispute_id: str, *, url: str, description: str = "") -> ActionResult:
        return self._post(f"/disputes/{dispute_id}/evidence/", {"url": url, "description": description})

    def list_evidence(self, dispute_id: str) -> ActionResult:
        return self._get(f"/disputes/{dispute_id}/evidence/")

    def delete_evidence(self, dispute_id: str, evidence_id: str) -> ActionResult:
        return self._delete(f"/disputes/{dispute_id}/evidence/{evidence_id}/")
