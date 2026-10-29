"""
Full CRUD for Listings, treated as a black box. The asymmetry in permissions between `update`
and `destroy` is worth noting (apps/listings/controller/listing_controller.py::get_permissions):
`update`/`partial_update`/`status` allow `(IsOwner | IsModerator | IsAdmin)`, whereas `destroy`
allows only `(IsOwner | IsAdmin)`—excluding the moderator. This is an intentional distinction
(a moderator can edit or unpublish a problematic listing, but does not have the authority to
physically delete it); it is not a bug.
"""
from __future__ import annotations

import pytest

from tests_e2e.fixtures.data import listing_payload, register_payload

pytestmark = pytest.mark.django_db(transaction=True)


class TestListingCreateAndRetrieve:
    def test_landlord_can_create_listing_always_as_draft(self, landlord):
        result = landlord.listings.create(listing_payload())

        assert result.status == 201, result.data
        assert result.data["status"] == "draft"

    def test_tenant_cannot_create_listing(self, tenant):
        result = tenant.listings.create(listing_payload())

        assert result.status == 403, result.data

    def test_owner_can_retrieve_own_draft_listing(self, landlord):
        created = landlord.listings.create(listing_payload())
        listing_id = created.data["id"]

        result = landlord.listings.get(listing_id)

        assert result.status == 200, result.data


class TestListingUpdate:
    def test_owner_can_update_own_listing(self, landlord):
        created = landlord.listings.create(listing_payload())
        listing_id = created.data["id"]

        result = landlord.listings.update(listing_id, {"title": "Updated title"})

        assert result.status == 200, result.data
        assert result.data["title"] == "Updated title"

    def test_stranger_cannot_update_someone_elses_listing(self, landlord, new_actor):
        created = landlord.listings.create(listing_payload())
        listing_id = created.data["id"]

        stranger = new_actor()
        stranger.auth.register(**register_payload(role="landlord", prefix="stranger"))

        result = stranger.listings.update(listing_id, {"title": "Hijacked"})

        assert result.status == 403, result.data

    def test_moderator_can_update_someone_elses_listing(self, landlord, moderator):
        """update is permitted (IsOwner | IsModerator | IsAdmin) — unlike
        destroy below."""
        created = landlord.listings.create(listing_payload())
        listing_id = created.data["id"]

        result = moderator.listings.update(listing_id, {"title": "Moderated title"})

        assert result.status == 200, result.data

    def test_changing_type_after_creation_is_rejected(self, landlord):
        """The 'type' field is immutable—the service explicitly checks this against the raw
        `request.data`, rather than `validated_data` (in fact, `ListingUpdateSerializer`
        does not even include 'type' in its `fields`, so standard serialization would not
        have caught this)."""
        created = landlord.listings.create(listing_payload(type="apartment"))
        listing_id = created.data["id"]

        result = landlord.listings.update(listing_id, {"type": "hotel"})

        assert result.status == 400, result.data


class TestListingDelete:
    def test_owner_can_delete_own_listing(self, landlord):
        created = landlord.listings.create(listing_payload())
        listing_id = created.data["id"]

        delete_result = landlord.listings.delete(listing_id)
        assert delete_result.status in (200, 204), delete_result.data

        get_result = landlord.listings.get(listing_id)
        assert get_result.status == 404, get_result.data

    def test_moderator_cannot_delete_someone_elses_listing(self, landlord, moderator):
        """There is an asymmetry compared to the `update` operation above: `destroy`
        requires `(IsOwner | IsAdmin)`—specifically *excluding* `IsModerator`. This
        is intentional, not a bug, but it is worth verifying explicitly."""
        created = landlord.listings.create(listing_payload())
        listing_id = created.data["id"]

        result = moderator.listings.delete(listing_id)

        assert result.status == 403, result.data

    def test_admin_can_delete_someone_elses_listing(self, landlord, admin_actor):
        created = landlord.listings.create(listing_payload())
        listing_id = created.data["id"]

        result = admin_actor.listings.delete(listing_id)

        assert result.status in (200, 204), result.data


class TestListingVisibilityAndListing:
    def test_public_list_shows_only_published_active_listings(self, landlord, new_actor):
        draft = landlord.listings.create(listing_payload())
        published = landlord.listings.create(listing_payload())
        landlord.listings.publish(published.data["id"])

        guest = new_actor()
        result = guest.listings.list()

        assert result.status == 200, result.data
        ids = [item["id"] for item in result.data["results"]] if "results" in result.data else [item["id"] for item in result.data]
        assert published.data["id"] in ids
        assert draft.data["id"] not in ids

    def test_mine_shows_all_own_listings_regardless_of_status(self, landlord):
        draft = landlord.listings.create(listing_payload())
        published = landlord.listings.create(listing_payload())
        landlord.listings.publish(published.data["id"])

        result = landlord.listings.mine()

        assert result.status == 200, result.data
        ids = [item["id"] for item in result.data["results"]] if "results" in result.data else [item["id"] for item in result.data]
        assert draft.data["id"] in ids
        assert published.data["id"] in ids

    def test_tenant_cannot_access_mine_endpoint(self, tenant):
        result = tenant.listings.mine()

        assert result.status == 403, result.data

    def test_toggle_active_hides_published_listing_from_public_list(self, landlord, new_actor):
        created = landlord.listings.create(listing_payload())
        listing_id = created.data["id"]
        landlord.listings.publish(listing_id)

        toggle_result = landlord.listings.toggle_active(listing_id)
        assert toggle_result.status == 200, toggle_result.data
        assert toggle_result.data["is_active"] is False

        guest = new_actor()
        result = guest.listings.list()
        ids = [item["id"] for item in result.data["results"]] if "results" in result.data else [item["id"] for item in result.data]
        assert listing_id not in ids
