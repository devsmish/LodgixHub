from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import LogModel


class NotificationLog(LogModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    is_read = models.BooleanField(default=False)

    def clean(self):
        super().clean()
        if not self.message.strip():
            raise ValidationError(
                {"message": _("Notification message cannot be empty.")}
            )
