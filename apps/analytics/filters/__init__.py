from django.utils.dateparse import parse_datetime


def _parse_query_datetime(value: str):
    """
    Parses an ISO 8601 date/time string from a query parameter.

    A '+HH:MM' (timezone offset) is decoded as a space if the client passed
    it without %2B encoding (standard `application/x-www-form-urlencoded`
    behavior) — for example, by naively inserting the output of
    `datetime.isoformat()` directly into the URL. Since ISO 8601 datetime
    strings use 'T' as the date/time separator (not a space), any space
    found in such a string represents a mangled '+', and it is safe to
    restore it before parsing.
    """
    parsed = parse_datetime(value)
    if parsed is not None:
        return parsed
    if " " in value:
        return parse_datetime(value.replace(" ", "+"))
    return None


def apply_date_range(
    queryset, date_from: str = None, date_to: str = None, date_field: str = "created_at"
):
    """Applies an optional date range filter (ISO 8601 in query parameters)."""
    if date_from:
        parsed = _parse_query_datetime(date_from)
        if parsed:
            queryset = queryset.filter(**{f"{date_field}__gte": parsed})
    if date_to:
        parsed = _parse_query_datetime(date_to)
        if parsed:
            queryset = queryset.filter(**{f"{date_field}__lte": parsed})
    return queryset
