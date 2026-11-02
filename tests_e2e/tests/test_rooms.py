"""
Regression tests for a bug:
The endpoint `GET /listings/{listing_id}/rooms/` initially failed to check the visibility
of the listing itself. While a draft listing was inaccessible via `GET /listings/{id}/`
(returning a 404 for unauthorized users or guests), its list of rooms remained fully
exposed—accessible to both unauthorized authenticated users and anonymous guests (even
those without any token).

Fix: Endpoint now perform an initial check using `ListingService.can_view_detail(request.user,
listing)` and return a `404` following the same convention as `GET /listings/{id}/`.

This file acts as a "black box" test against a live server, verifying a matrix of user roles:
anonymous users/unauthorized users receive a 404 for draft listings;
owners/moderators/admins always receive a 200;
for published listings, all users receive a 200.
"""
from __future__ import annotations

import pytest

from tests_e2e.fixtures.data import listing_payload, register_payload

pytestmark = pytest.mark.django_db(transaction=True)


def _listing(landlord, *, listing_type: str = "apartment", published: bool = False, **overrides) -> str:
    payload = listing_payload(type=listing_type, **overrides)
    if listing_type != "apartment":
        payload.pop("rooms_count", None)

    result = landlord.listings.create(payload)
    assert result.ok, f"listing creation failed: {result.status} {result.data}"
    listing_id = result.data["id"]

    if published:
        publish_result = landlord.listings.publish(listing_id)
        assert publish_result.ok, f"publish failed: {publish_result.status} {publish_result.data}"

    return listing_id


def _stranger(new_actor):
    stranger = new_actor()
    stranger.auth.register(**register_payload(role="tenant", prefix="stranger"))
    return stranger


class TestRoomVisibility:
    def test_draft_listing_rooms_hidden_from_anonymous_guest(self, landlord, new_actor):
        listing_id = _listing(landlord, listing_type="hotel", published=False)
        landlord.rooms.create(listing_id, {"room_type": "single", "name": "Room 1", "max_guests": 2, "rooms_available_count": 1})

        guest = new_actor()

        result = guest.rooms.list_for_listing(listing_id)

        assert result.status == 404, result.data

    def test_draft_listing_rooms_hidden_from_authenticated_outsider(self, landlord, new_actor):
        listing_id = _listing(landlord, listing_type="hotel", published=False)
        landlord.rooms.create(listing_id, {"room_type": "single", "name": "Room 1", "max_guests": 2, "rooms_available_count": 1})

        outsider = _stranger(new_actor)

        result = outsider.rooms.list_for_listing(listing_id)

        assert result.status == 404, result.data

    def test_draft_listing_rooms_visible_to_owner(self, landlord):
        listing_id = _listing(landlord, listing_type="hotel", published=False)
        landlord.rooms.create(listing_id, {"room_type": "single", "name": "Room 1", "max_guests": 2, "rooms_available_count": 1})

        result = landlord.rooms.list_for_listing(listing_id)

        assert result.status == 200, result.data
        assert len(result.data) == 1

    def test_draft_listing_rooms_visible_to_moderator_and_admin(self, landlord, moderator, admin_actor):
        listing_id = _listing(landlord, listing_type="hotel", published=False)
        landlord.rooms.create(listing_id, {"room_type": "single", "name": "Room 1", "max_guests": 2, "rooms_available_count": 1})

        assert moderator.rooms.list_for_listing(listing_id).status == 200
        assert admin_actor.rooms.list_for_listing(listing_id).status == 200

    def test_published_listing_rooms_visible_to_anyone(self, landlord, new_actor):
        listing_id = _listing(landlord, listing_type="hotel", published=True)
        landlord.rooms.create(listing_id, {"room_type": "single", "name": "Room 1", "max_guests": 2, "rooms_available_count": 1})

        guest = new_actor()
        outsider = _stranger(new_actor)

        assert guest.rooms.list_for_listing(listing_id).status == 200
        assert outsider.rooms.list_for_listing(listing_id).status == 200

    def test_rooms_of_nonexistent_listing_return_404(self, new_actor):
        guest = new_actor()

        result = guest.rooms.list_for_listing("00000000-0000-0000-0000-000000000000")

        assert result.status == 404, result.data


class TestRoomCRUD:
    def test_owner_can_update_own_room(self, landlord):
        listing_id = _listing(landlord, listing_type="hotel", published=False)
        created = landlord.rooms.create(listing_id, {"room_type": "single", "name": "Room 1", "max_guests": 2, "rooms_available_count": 1})
        room_id = created.data["id"]

        result = landlord.rooms.update(listing_id, room_id, {"name": "Deluxe Room"})

        assert result.status == 200, result.data
        assert result.data["name"] == "Deluxe Room"

    def test_stranger_cannot_update_someone_elses_room(self, landlord, new_actor):
        listing_id = _listing(landlord, listing_type="hotel", published=False)
        created = landlord.rooms.create(listing_id, {"room_type": "single", "name": "Room 1", "max_guests": 2, "rooms_available_count": 1})
        room_id = created.data["id"]

        stranger = _stranger(new_actor)
        result = stranger.rooms.update(listing_id, room_id, {"name": "Hijacked"})

        assert result.status in (403, 404), result.data

    def test_owner_can_delete_own_room(self, landlord):
        listing_id = _listing(landlord, listing_type="hotel", published=False)
        created = landlord.rooms.create(listing_id, {"room_type": "single", "name": "Room 1", "max_guests": 2, "rooms_available_count": 1})
        room_id = created.data["id"]

        result = landlord.rooms.delete(listing_id, room_id)

        assert result.status in (200, 204), result.data
