from datetime import datetime, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied

from apps.bookings.choices import BookingStatus
from apps.bookings.constants import (
    LAST_MINUTE_DISCOUNT_NEXT_DAY,
    LAST_MINUTE_DISCOUNT_SAME_DAY,
    TENANT_FREE_CANCEL_CUTOFF_HOURS,
)
from apps.bookings.errors import (
    BookingCancelWindowExpiredError,
    BookingNotAvailableError,
    BookingTransitionNotAllowedError,
    CancellationReasonRequiredError,
    ListingNotBookableError,
)
from apps.bookings.models import Booking
from apps.bookings.repositories import BookingRepository
from apps.listings.choices import ListingStatus
from apps.listings.models import Listing, Room


class BookingService:

    def __init__(self, repository: BookingRepository = None):
        self.repository = repository or BookingRepository()

    # list of your bookings

    def list_for_user(self, user):
        return (
            self.repository.get_all_queryset()
            .filter(
                Q(tenant=user) | Q(listing__owner=user) | Q(room__listing__owner=user)
            )
            .distinct()
        )

    @staticmethod
    def is_participant(booking, user) -> bool:
        landlord = booking.get_landlord()
        return booking.tenant_id == user.id or (landlord and landlord.id == user.id)

    # validation sequence for creation

    @transaction.atomic
    def create_booking(
        self,
        *,
        tenant,
        listing_id,
        room_id,
        check_in_date,
        check_out_date,
        guests_count,
    ):
        is_room = room_id is not None
        target, listing = self._resolve_target(listing_id, room_id)

        self._guard_bookable(listing)
        self._guard_availability(target, check_in_date, check_out_date, is_room=is_room)

        total_price = self._calculate_price(
            target=target,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            is_room=is_room,
        )
        deposit_amount = self._calculate_deposit(listing, total_price)

        booking = Booking(
            tenant=tenant,
            listing=None if is_room else target,
            room=target if is_room else None,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            guests_count=guests_count,
            total_price=total_price,
            deposit_amount=deposit_amount,
        )

        booking.save()
        return booking

    @staticmethod
    def _resolve_target(listing_id, room_id):
        if listing_id:
            listing = Listing.all_objects.filter(id=listing_id).first()
            if listing is None:
                raise NotFound("Ad not found.")
            return listing, listing

        room = Room.all_objects.filter(id=room_id).select_related("listing").first()
        if room is None:
            raise NotFound("Room not found.")
        return room, room.listing

    @staticmethod
    def _guard_bookable(listing):
        """listing.status == published AND listing.is_active == True."""
        if listing.status != ListingStatus.PUBLISHED or not listing.is_active:
            raise ListingNotBookableError()

    @staticmethod
    def _guard_availability(target, check_in_date, check_out_date, *, is_room):
        """Availability formula — error 409 if available <= 0."""
        overlap = Q(
            check_in_date__lt=check_out_date,
            check_out_date__gt=check_in_date,
            status__in=(BookingStatus.PENDING, BookingStatus.CONFIRMED),
        )
        if is_room:
            busy = Booking.objects.filter(overlap, room=target).count()
            if busy >= target.rooms_available_count:
                raise BookingNotAvailableError()
        else:
            if Booking.objects.filter(overlap, listing=target).exists():
                raise BookingNotAvailableError()

    @staticmethod
    def _calculate_price(*, target, check_in_date, check_out_date, is_room):
        """the current price from PriceHistory for the check-in date,
        a 15%/10% discount for bookings for today/tomorrow, multiplied by the number
        of nights. The result is a fixed value: it is returned
        once here and is not recalculated anywhere else."""
        from apps.pricing.models import PriceHistory

        price_entry = PriceHistory.objects.effective_on(
            check_in_date,
            listing=None if is_room else target,
            room=target if is_room else None,
        ).first()
        if price_entry is None:
            raise ListingNotBookableError(
                "A price has not yet been set for this listing/room for this date."
            )

        base_price = price_entry.price
        today = timezone.localdate()
        if check_in_date == today:
            base_price = base_price * (1 - Decimal(str(LAST_MINUTE_DISCOUNT_SAME_DAY)))
        elif check_in_date == today + timedelta(days=1):
            base_price = base_price * (1 - Decimal(str(LAST_MINUTE_DISCOUNT_NEXT_DAY)))

        nights = (check_out_date - check_in_date).days
        return (base_price * nights).quantize(Decimal("0.01"))

    @staticmethod
    def _calculate_deposit(listing, total_price):
        if not listing.deposit_required:
            return Decimal("0.00")
        return (total_price * Decimal(listing.deposit_percent) / Decimal(100)).quantize(
            Decimal("0.01")
        )

    # Confirmation/rejection by owner only

    def confirm(self, *, booking, actor):
        self._guard_is_landlord(booking, actor)
        if booking.status != BookingStatus.PENDING:
            raise BookingTransitionNotAllowedError()

        booking.status = BookingStatus.CONFIRMED
        booking.confirmed_at = timezone.now()
        booking.save(update_fields=["status", "confirmed_at", "updated_at"])
        return booking

    def reject(self, *, booking, actor):
        self._guard_is_landlord(booking, actor)
        if booking.status != BookingStatus.PENDING:
            raise BookingTransitionNotAllowedError()

        booking.status = BookingStatus.REJECTED
        booking.save(update_fields=["status", "updated_at"])
        return booking

    @staticmethod
    def _guard_is_landlord(booking, actor):
        landlord = booking.get_landlord()
        if landlord is None or landlord.id != actor.id:
            raise PermissionDenied(
                "Only the owner of the listing can perform this action."
            )

    # Cancellation: tenant — up to 24 hours in advance; owner — with a reason.

    def cancel(self, *, booking, actor, cancellation_reason=None):
        is_tenant = booking.tenant_id == actor.id
        landlord = booking.get_landlord()
        is_landlord = landlord is not None and landlord.id == actor.id

        if not (is_tenant or is_landlord):
            raise PermissionDenied("You are not a participant in this booking.")

        if booking.status not in (BookingStatus.PENDING, BookingStatus.CONFIRMED):
            raise BookingTransitionNotAllowedError()

        if is_landlord:
            new_status = self._cancel_as_landlord(cancellation_reason)
        else:
            new_status = self._cancel_as_tenant(booking)

        booking.status = new_status
        booking.cancelled_at = timezone.now()
        booking.cancelled_by = actor
        booking.cancellation_reason = cancellation_reason
        booking.save(
            update_fields=[
                "status",
                "cancelled_at",
                "cancelled_by",
                "cancellation_reason",
                "updated_at",
            ]
        )
        return booking

    def _cancel_as_tenant(self, booking):
        deadline = self._tenant_cancel_deadline(booking)
        if timezone.now() > deadline:
            raise BookingCancelWindowExpiredError()
        return BookingStatus.CANCELLED_BY_TENANT

    @staticmethod
    def _tenant_cancel_deadline(booking):
        """
        No later than 24 hours before the check-in date. The check-in time
        is based on the actual check-in time for the listing/room (TimePolicy).
        """
        target = booking.room if booking.room else booking.listing
        check_in_dt = timezone.make_aware(
            datetime.combine(booking.check_in_date, target.check_in_time)
        )
        return check_in_dt - timedelta(hours=TENANT_FREE_CANCEL_CUTOFF_HOURS)

    @staticmethod
    def _cancel_as_landlord(cancellation_reason):
        if cancellation_reason is None:
            raise CancellationReasonRequiredError()
        # TODO(apps.notifications): automated apology email to the tenant.
        return BookingStatus.CANCELLED_BY_LANDLORD
