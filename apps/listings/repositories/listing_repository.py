from apps.listings.models import Listing


class ListingRepository:

    @staticmethod
    def get_all_queryset():
        """Sees everything, including soft-deleted items and all statuses — for the owner,
        moderator, or admin during targeted operations. (update/destroy/status/...)."""
        return Listing.all_objects.select_related("address", "owner").prefetch_related(
            "amenities"
        )

    @staticmethod
    def get_active_queryset():
        return Listing.objects.select_related("address", "owner").prefetch_related(
            "amenities"
        )

    @staticmethod
    def get_by_id_any(listing_id):
        return (
            Listing.all_objects.filter(id=listing_id)
            .select_related("address", "owner")
            .prefetch_related("amenities")
            .first()
        )

    @staticmethod
    def get_for_owner(owner):
        return (
            Listing.all_objects.filter(owner=owner)
            .select_related("address")
            .order_by("-created_at")
        )
