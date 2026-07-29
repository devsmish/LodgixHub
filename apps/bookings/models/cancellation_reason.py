from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.bookings.validators.cancellation_reason_validators import cancellation_reason_code_validator
from core.models import BaseModel


class CancellationReason(BaseModel):

    code = models.CharField(
        max_length=50,
        unique=True,
        validators=[cancellation_reason_code_validator],
        verbose_name=_("Code"),
        help_text=_(
            "Free-form unique code (^[A-Z_]+$). "
            "StandardCancellationReason only seeds the initial set."
        ),
    )
    description = models.CharField(max_length=255, verbose_name=_("Description"))

    class Meta:
        verbose_name = _("Cancellation Reason")
        verbose_name_plural = _("Cancellation Reasons")

    def __str__(self):
        return self.description
