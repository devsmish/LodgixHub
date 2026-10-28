"""
Regression tests for a bug:
The endpoints `GET /listings/{listing_id}/photos/` and `GET /listings/{listing_id}/rooms/`
initially failed to check the visibility of the listing itself. While a draft listing was
inaccessible via `GET /listings/{id}/` (returning a 404 for unauthorized users or guests),
its photo gallery and list of rooms remained fully exposed—accessible to both unauthorized
authenticated users and anonymous guests (even those without any token).

Fix: Both endpoints now perform an initial check using
`ListingService.can_view_detail(request.user, listing)` and return a `404` following the
same convention as `GET /listings/{id}/`.

This file acts as a "black box" test against a live server, verifying a matrix of user roles:
anonymous users/unauthorized users receive a 404 for draft listings;
owners/moderators/admins always receive a 200;
for published listings, all users receive a 200.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tests_e2e.fixtures.data import listing_payload, register_payload

pytestmark = pytest.mark.django_db(transaction=True)

TEST_PHOTO_PATH = Path(__file__).parent.parent / "fixtures" / "assets" / "test_photo.jpg"


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


class TestPhotoVisibility:
    def test_draft_listing_photos_hidden_from_anonymous_guest(self, landlord, new_actor):
        listing_id = _listing(landlord, published=False)
        landlord.photos.upload(listing_id, image_bytes=TEST_PHOTO_PATH.read_bytes())

        guest = new_actor()  # ни регистрации, ни токена — анонимный гость

        result = guest.photos.list_for_listing(listing_id)

        assert result.status == 404, result.data

    def test_draft_listing_photos_hidden_from_authenticated_outsider(self, landlord, new_actor):
        listing_id = _listing(landlord, published=False)
        landlord.photos.upload(listing_id, image_bytes=TEST_PHOTO_PATH.read_bytes())

        outsider = _stranger(new_actor)

        result = outsider.photos.list_for_listing(listing_id)

        assert result.status == 404, result.data

    def test_draft_listing_photos_visible_to_owner(self, landlord):
        listing_id = _listing(landlord, published=False)
        landlord.photos.upload(listing_id, image_bytes=TEST_PHOTO_PATH.read_bytes())

        result = landlord.photos.list_for_listing(listing_id)

        assert result.status == 200, result.data
        assert len(result.data) == 1

    def test_draft_listing_photos_visible_to_moderator(self, landlord, moderator):
        listing_id = _listing(landlord, published=False)
        landlord.photos.upload(listing_id, image_bytes=TEST_PHOTO_PATH.read_bytes())

        result = moderator.photos.list_for_listing(listing_id)

        assert result.status == 200, result.data

    def test_draft_listing_photos_visible_to_admin(self, landlord, admin_actor):
        listing_id = _listing(landlord, published=False)
        landlord.photos.upload(listing_id, image_bytes=TEST_PHOTO_PATH.read_bytes())

        result = admin_actor.photos.list_for_listing(listing_id)

        assert result.status == 200, result.data

    def test_published_listing_photos_visible_to_anyone(self, landlord, new_actor):
        listing_id = _listing(landlord, published=True)
        landlord.photos.upload(listing_id, image_bytes=TEST_PHOTO_PATH.read_bytes())

        guest = new_actor()
        outsider = _stranger(new_actor)

        assert guest.photos.list_for_listing(listing_id).status == 200
        assert outsider.photos.list_for_listing(listing_id).status == 200
        assert landlord.photos.list_for_listing(listing_id).status == 200

    def test_photos_of_nonexistent_listing_return_404(self, new_actor):
        guest = new_actor()

        result = guest.photos.list_for_listing("00000000-0000-0000-0000-000000000000")

        assert result.status == 404, result.data

    def test_stranger_cannot_upload_photo_to_someone_elses_listing(self, landlord, new_actor):
        """Verification that uploads are protected just as strictly as read operations."""
        listing_id = _listing(landlord, published=True)

        stranger = new_actor()
        stranger.auth.register(**register_payload(role="landlord", prefix="stranger"))

        result = stranger.photos.upload(listing_id, image_bytes=TEST_PHOTO_PATH.read_bytes())

        assert result.status in (403, 404), result.data


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
