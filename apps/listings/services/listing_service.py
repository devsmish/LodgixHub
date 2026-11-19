from django.db import transaction
from django.db.models import Q

from apps.listings.choices import ListingStatus
from apps.listings.errors import (
    ListingHasActiveBookingsError,
    ListingStatusTransitionNotAllowedError,
    ListingTypeImmutableError,
)
from apps.listings.filters import ListingFilter
from apps.listings.models import Address, Listing
from apps.listings.repositories import ListingRepository
from apps.security.constants import GROUP_ADMIN, GROUP_MODERATOR


class ListingService:

    def __init__(self, repository: ListingRepository = None):
        self.repository = repository or ListingRepository()

    def list_listings(self, *, user, query_params):
        queryset = self._get_visible_queryset(user)
        queryset = ListingFilter(query_params).apply(queryset)
        queryset = self._apply_availability_filter(queryset, query_params)
        self._record_search_if_keyword_present(user, query_params, queryset)
        return queryset

    def _get_visible_queryset(self, user):
        """Guest/user — only published + active; owner — plus their own
        draft/hidden/rejected; moderator/admin — everything."""
        base_queryset = self.repository.get_all_queryset()

        if not (user and user.is_authenticated):
            return base_queryset.filter(status=ListingStatus.PUBLISHED, is_active=True)

        if self._is_moderator_or_admin(user):
            return base_queryset

        return base_queryset.filter(
            Q(status=ListingStatus.PUBLISHED, is_active=True) | Q(owner=user)
        )

    @staticmethod
    def _is_moderator_or_admin(user) -> bool:
        if user.is_superuser:
            return True
        return user.groups.filter(name__in=(GROUP_MODERATOR, GROUP_ADMIN)).exists()

    def _apply_availability_filter(self, queryset, query_params):
        """Show only properties available for the selected dates."""
        check_in = query_params.get("check_in")
        check_out = query_params.get("check_out")
        if not (check_in and check_out):
            return queryset

        from apps.bookings.guards.availability_guard import get_available_listing_ids

        available_ids = get_available_listing_ids(check_in, check_out, queryset)
        return queryset.filter(id__in=available_ids)

    @staticmethod
    def _record_search_if_keyword_present(user, query_params, queryset):
        """Logging the search keyword to SearchHistory with every query."""
        keyword = query_params.get("q")
        if not keyword:
            return

        from apps.analytics.services import SearchHistoryService

        SearchHistoryService().record_search(
            user=user if (user and user.is_authenticated) else None,
            keyword=keyword,
            results_count=queryset.count(),
        )

    def get_visible_detail(self, *, user, listing_id, session_key=None):
        listing = self.repository.get_by_id_any(listing_id)
        if listing is None or listing.is_deleted:
            return None
        if not self.can_view_detail(user, listing):
            return None

        self._record_view(listing, user, session_key)
        listing.refresh_from_db(fields=["views_count"])
        return listing

    def can_view_detail(self, user, listing) -> bool:
        if listing.is_visible_to_public:
            return True
        if not (user and user.is_authenticated):
            return False
        return listing.owner_id == user.id or self._is_moderator_or_admin(user)

    @staticmethod
    def _record_view(listing, user, session_key):
        """Increment `views_count` + record in `ViewHistory` (with 15-minute
        deduplication — a rule already implemented within `ViewHistoryService`)."""
        from apps.analytics.services import ViewHistoryService

        ViewHistoryService().record_view(
            listing=listing,
            user=user if (user and user.is_authenticated) else None,
            session_key=session_key,
        )

    # --- CRUD ---

    @transaction.atomic
    def create_listing(self, *, owner, validated_data):
        address_data = validated_data.pop("address")
        address = Address.objects.create(**address_data)
        return Listing.objects.create(
            owner=owner,
            address=address,
            status=ListingStatus.DRAFT,
            **validated_data,
        )

    @transaction.atomic
    def update_listing(self, *, listing, validated_data, raw_data):
        self._guard_type_immutable(listing, raw_data)
        self._apply_address_update(listing, validated_data.pop("address", None))
        self._apply_listing_fields(listing, validated_data)
        return listing

    @staticmethod
    def _guard_type_immutable(listing, raw_data):
        """The 'type' is immutable after creation."""
        if "type" in raw_data and str(raw_data["type"]) != listing.type:
            raise ListingTypeImmutableError()

    @staticmethod
    def _apply_address_update(listing, address_data):
        if not address_data:
            return
        for field, value in address_data.items():
            setattr(listing.address, field, value)
        listing.address.full_clean()
        listing.address.save()

    @staticmethod
    def _apply_listing_fields(listing, validated_data):
        for field, value in validated_data.items():
            setattr(listing, field, value)
        listing.full_clean()
        listing.save()

    @transaction.atomic
    def delete_listing(self, listing):
        """Prohibited if there is a booking with a "pending" or "confirmed" status."""
        from apps.bookings.guards.listing_guard import listing_has_active_bookings

        if listing_has_active_bookings(listing):
            raise ListingHasActiveBookingsError()
        listing.delete()
        return listing

    def toggle_active(self, listing):
        listing.is_active = not listing.is_active
        listing.save(update_fields=["is_active", "updated_at"])
        return listing

    # --- STATUS ---

    def update_status(self, *, listing, new_status, actor):
        self._validate_status_transition(
            listing=listing, new_status=new_status, actor=actor
        )
        listing.status = new_status
        listing.save(update_fields=["status", "updated_at"])
        return listing

    def _validate_status_transition(self, *, listing, new_status, actor):
        is_owner = listing.owner_id == actor.id
        is_moderator_or_admin = self._is_moderator_or_admin(actor)

        if is_moderator_or_admin:
            self._validate_moderator_transition(new_status)
        elif is_owner:
            self._validate_owner_transition(listing, new_status)
        else:
            raise ListingStatusTransitionNotAllowedError()

    @staticmethod
    def _validate_owner_transition(listing, new_status):
        """The owner publishes it themselves: draft -> published."""
        allowed = (
            listing.status == ListingStatus.DRAFT
            and new_status == ListingStatus.PUBLISHED
        )
        if not allowed:
            raise ListingStatusTransitionNotAllowedError()

    @staticmethod
    def _validate_moderator_transition(new_status):
        """Moderator/admin — post-moderation: hidden/rejected (and published)."""
        allowed_targets = (
            ListingStatus.HIDDEN,
            ListingStatus.REJECTED,
            ListingStatus.PUBLISHED,
        )
        if new_status not in allowed_targets:
            raise ListingStatusTransitionNotAllowedError()

    def get_mine(self, owner):
        return self.repository.get_for_owner(owner)

    @transaction.atomic
    def set_amenities(self, *, listing, amenities):
        listing.amenities.set(amenities)
        return listing
