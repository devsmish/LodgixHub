from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.listings.models import Listing
from core.models import LogModel


class SearchHistory(LogModel):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="search_history",
        verbose_name=_("User"),
        help_text=_("Null for unauthenticated guest search."),
    )
    keyword = models.CharField(max_length=255, verbose_name=_("Keyword"))
    results_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Results Count"),
        help_text=_("Number of listings matched by this query."),
    )

    class Meta:
        verbose_name = _("Search History")
        verbose_name_plural = _("Search History")
        indexes = [
            models.Index(fields=["keyword"]),
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self):
        results = self.results_count if self.results_count is not None else "?"
        return f'"{self.keyword}" ({results} results)'


class ViewHistory(LogModel):

    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="view_history",
        verbose_name=_("Listing"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="view_history",
        verbose_name=_("User"),
        help_text=_("Null for unauthenticated guest view."),
    )
    session_key = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        verbose_name=_("Session Key"),
        help_text=_("Django session id, used for guest view dedup instead of IP."),
    )

    class Meta:
        verbose_name = _("View History")
        verbose_name_plural = _("View History")
        indexes = [
            # For ad popularity and history queries.
            models.Index(fields=["listing", "created_at"]),
            # For a quick deduplication check during every view.
            models.Index(fields=["listing", "user", "session_key"]),
        ]

    def __str__(self):
        return f"{self.listing_id} viewed at {self.created_at:%Y-%m-%d %H:%M}"
