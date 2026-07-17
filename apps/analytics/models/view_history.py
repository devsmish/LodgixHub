from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.listings.models import Listing
from core.models import LogModel


class ViewHistory(LogModel):
    """
    Раздел 2.3 ТЗ. Лог просмотра объявления, иммутабелен.

    session_key используется для дедупликации просмотров гостя БЕЗ хранения
    IP-адреса (более щадящий вариант с точки зрения GDPR — проект развёрнут
    для аудитории в Германии).
    """

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
            # Для запросов популярности и истории по объявлению.
            models.Index(fields=["listing", "created_at"]),
            # Для быстрой проверки дедупликации при каждом просмотре.
            models.Index(fields=["listing", "user", "session_key"]),
        ]

    def __str__(self):
        return f"{self.listing_id} viewed at {self.created_at:%Y-%m-%d %H:%M}"
