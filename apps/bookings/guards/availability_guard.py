import calendar
from datetime import date, timedelta

from django.db.models import Count

from apps.bookings.choices import BookingStatus
from apps.bookings.models import Booking
from apps.listings.choices import ListingType
from apps.listings.models import Room

ACTIVE_BOOKING_STATUSES = (BookingStatus.PENDING, BookingStatus.CONFIRMED)


def get_available_listing_ids(check_in, check_out, queryset):
    """
    Returns a set of listing IDs from the `queryset`
    available for the date range (check_in, check_out).
    A listing is available if at least one of its rooms is free.
    """
    listing_rows = list(queryset.values("id", "type"))
    apartment_ids = {
        row["id"] for row in listing_rows if row["type"] == ListingType.APARTMENT
    }
    multi_room_listing_ids = {row["id"] for row in listing_rows} - apartment_ids

    overlap_filter = dict(check_in_date__lt=check_out, check_out_date__gt=check_in)

    available_apartment_ids = _get_available_apartment_ids(
        apartment_ids, overlap_filter
    )
    available_multi_room_ids = _get_available_multi_room_listing_ids(
        multi_room_listing_ids, overlap_filter
    )

    return available_apartment_ids | available_multi_room_ids


def _get_available_apartment_ids(apartment_ids, overlap_filter):
    busy_ids = set(
        Booking.objects.filter(
            status__in=ACTIVE_BOOKING_STATUSES,
            listing_id__in=apartment_ids,
            **overlap_filter,
        ).values_list("listing_id", flat=True)
    )
    return apartment_ids - busy_ids


def _get_available_multi_room_listing_ids(listing_ids, overlap_filter):
    rooms = list(
        Room.objects.filter(listing_id__in=listing_ids).values(
            "id", "listing_id", "rooms_available_count"
        )
    )
    room_ids = [room["id"] for room in rooms]

    busy_counts_by_room = dict(
        Booking.objects.filter(
            status__in=ACTIVE_BOOKING_STATUSES,
            room_id__in=room_ids,
            **overlap_filter,
        )
        .values("room_id")
        .annotate(busy=Count("id"))
        .values_list("room_id", "busy")
    )

    available_listing_ids = set()
    for room in rooms:
        busy = busy_counts_by_room.get(room["id"], 0)
        if busy < room["rooms_available_count"]:
            available_listing_ids.add(room["listing_id"])
    return available_listing_ids


def get_listing_calendar(listing, year, month):
    """
    Monthly availability calendar for the listing/unit.
    Returns {day (int, 1..N): bool is_available}, determining availability
    for the interval [day, day+1):
    apartment — occupied if it overlaps with an active booking for the listing itself;
    hotel/hostel — available if at least one room is free on that day.
    """
    _, days_in_month = calendar.monthrange(year, month)
    month_start = date(year, month, 1)
    month_end = date(year, month, days_in_month) + timedelta(days=1)

    if listing.type == ListingType.APARTMENT:
        return _get_apartment_calendar(
            listing, year, month, days_in_month, month_start, month_end
        )
    return _get_multi_room_calendar(
        listing, year, month, days_in_month, month_start, month_end
    )


def _get_apartment_calendar(
    listing, year, month, days_in_month, month_start, month_end
):
    calendar_map = {day: True for day in range(1, days_in_month + 1)}

    bookings = Booking.objects.filter(
        listing=listing,
        status__in=ACTIVE_BOOKING_STATUSES,
        check_in_date__lt=month_end,
        check_out_date__gt=month_start,
    ).values_list("check_in_date", "check_out_date")

    for check_in_date, check_out_date in bookings:
        for day in range(1, days_in_month + 1):
            current = date(year, month, day)
            if check_in_date <= current < check_out_date:
                calendar_map[day] = False

    return calendar_map


def _get_multi_room_calendar(
    listing, year, month, days_in_month, month_start, month_end
):
    rooms = list(
        Room.objects.filter(listing=listing).values("id", "rooms_available_count")
    )
    if not rooms:
        return {day: False for day in range(1, days_in_month + 1)}

    room_capacity = {room["id"]: room["rooms_available_count"] for room in rooms}
    busy_by_day_room = {
        day: {room_id: 0 for room_id in room_capacity}
        for day in range(1, days_in_month + 1)
    }

    bookings = Booking.objects.filter(
        room_id__in=room_capacity.keys(),
        status__in=ACTIVE_BOOKING_STATUSES,
        check_in_date__lt=month_end,
        check_out_date__gt=month_start,
    ).values_list("room_id", "check_in_date", "check_out_date")

    for room_id, check_in_date, check_out_date in bookings:
        for day in range(1, days_in_month + 1):
            current = date(year, month, day)
            if check_in_date <= current < check_out_date:
                busy_by_day_room[day][room_id] += 1

    calendar_map = {}
    for day in range(1, days_in_month + 1):
        calendar_map[day] = any(
            busy_by_day_room[day][room_id] < capacity
            for room_id, capacity in room_capacity.items()
        )
    return calendar_map
