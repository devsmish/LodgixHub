from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.notifications.choices import NotificationType
from core.models import LogModel


class NotificationLog(LogModel):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notification_logs",
        verbose_name=_("Recipient"),
        help_text=_("Nullable for system notifications without a specific recipient."),
    )
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType,
        verbose_name=_("Notification type"),
    )
    success = models.BooleanField(verbose_name=_("Success"))
    error_message = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name=_("Error message"),
        help_text=_("Only populated when success is False."),
    )

    class Meta:
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["notification_type"]),
        ]

    def clean(self):
        super().clean()
        # Populated only when success=False — a one-way check:
        # if success=True, error_message must be empty.
        if self.success and self.error_message:
            raise ValidationError(
                {
                    "error_message": _(
                        "error_message must be empty when success is True."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        status = "OK" if self.success else "FAILED"
        return f"{self.notification_type} -> {self.user_id or 'system'} [{status}]"
