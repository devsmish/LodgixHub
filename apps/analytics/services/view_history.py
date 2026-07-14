from datetime import timedelta

from django.utils import timezone

from apps.analytics.constants import VIEW_DEDUP_WINDOW_MINUTES
from apps.analytics.repositories.view_history import ViewHistoryRepository


class ViewHistoryService:
    """
    View deduplication rule: the service checks whether
    a record already exists for the same pair (listing+user, if authenticated,
    otherwise listing+session_key) within the last VIEW_DEDUP_WINDOW_MINUTES = 15.
    If one exists, the view is not counted again (protecting the popularity
    counter against inflation via simple page refreshes).

    Called from apps.listings.controller upon GET /api/listings/{id}/
    """

    def __init__(self, repository: ViewHistoryRepository | None = None):
        self.repository = repository or ViewHistoryRepository()

    def record_view(self, *, listing, user=None, session_key: str | None = None):
        is_authenticated = bool(user and user.is_authenticated)
        since = timezone.now() - timedelta(minutes=VIEW_DEDUP_WINDOW_MINUTES)

        already_counted = self.repository.exists_recent(
            listing=listing,
            user=user if is_authenticated else None,
            session_key=None if is_authenticated else session_key,
            since=since,
        )
        if already_counted:
            return None

        view = self.repository.create(
            listing=listing,
            user=user if is_authenticated else None,
            session_key=None if is_authenticated else session_key,
        )
        listing.increment_views_count()
        return view

    def get_my_history(self, user):
        return self.repository.get_for_user(user)
