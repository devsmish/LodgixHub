from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.bookings.choices import StandardCancellationReason
from core.models import BaseModel


class CancellationReason(BaseModel):
    code = models.CharField(
        max_length=50,
        unique=True,
        choices=StandardCancellationReason,
        verbose_name=_("Code"),
    )
    description = models.CharField(max_length=255, verbose_name=_("Description"))

    class Meta:
        verbose_name = _("Cancellation Reason")
        verbose_name_plural = _("Cancellation Reasons")

    def __str__(self):
        return self.description
