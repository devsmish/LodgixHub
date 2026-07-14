from datetime import datetime

from django.db.models import QuerySet

from apps.analytics.models import ViewHistory


class ViewHistoryRepository:

    @staticmethod
    def create(*, listing, user, session_key) -> ViewHistory:
        return ViewHistory.objects.create(
            listing=listing, user=user, session_key=session_key
        )

    @staticmethod
    def exists_recent(*, listing, user, session_key, since: datetime) -> bool:
        qs = ViewHistory.objects.filter(listing=listing, created_at__gte=since)
        if user is not None:
            qs = qs.filter(user=user)
        else:
            qs = qs.filter(user__isnull=True, session_key=session_key)
        return qs.exists()

    @staticmethod
    def get_for_user(user) -> QuerySet:
        return (
            ViewHistory.objects.filter(user=user)
            .select_related("listing")
            .order_by("-created_at")
        )
