from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import LogModel


class SearchHistory(LogModel):
    """
    The search query log is immutable.
    """

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
        help_text=_(
            "Number of listings matched by this query; null-count queries signal catalog gaps."
        ),
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
