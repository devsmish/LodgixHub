from __future__ import annotations

from tests_e2e.actions.api.base_api_action import BaseAPIAction
from tests_e2e.actions.base import ActionResult, ListingActions


class APIListingActions(BaseAPIAction, ListingActions):
    """POST /listings/, PATCH /listings/{id}/status/, GET /listings/{id}/.

    Only the minimum required for Booking scenarios has been implemented.
    """

    def create(self, payload: dict) -> ActionResult:
        return self._post("/listings/", payload)

    def publish(self, listing_id: str) -> ActionResult:
        return self._patch(f"/listings/{listing_id}/status/", {"status": "published"})

    def get(self, listing_id: str) -> ActionResult:
        return self._get(f"/listings/{listing_id}/")

    def set_price(self, listing_id: str, *, price: str, valid_from: str) -> ActionResult:
        """POST /listings/{listing_id}/price/ — falls outside the abstract
        `ListingActions` contract (there is currently no equivalent in the
        UI version, but it is required for any booking scenario): the booking
        service consults `PriceHistory` for a specific check-in date, rather
        than accessing `Listing.current_price` directly (see
        `apps/bookings/services/booking_service.py::_calculate_price`)."""
        return self._post(f"/listings/{listing_id}/price/", {"price": price, "valid_from": valid_from})
