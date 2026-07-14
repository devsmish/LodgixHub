from django.utils.dateparse import parse_datetime


def apply_date_range(
    queryset, date_from: str = None, date_to: str = None, date_field: str = "created_at"
):
    """Applies an optional date range filter (ISO 8601 in query parameters)."""
    if date_from:
        parsed = parse_datetime(date_from)
        if parsed:
            queryset = queryset.filter(**{f"{date_field}__gte": parsed})
    if date_to:
        parsed = parse_datetime(date_to)
        if parsed:
            queryset = queryset.filter(**{f"{date_field}__lte": parsed})
    return queryset
