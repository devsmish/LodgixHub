from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import BaseModel

validate_cancellation_reason_code = RegexValidator(
    regex=r"^[A-Z_]+$",
    message=_("Code must contain only uppercase letters and underscores."),
)


class CancellationReason(BaseModel):
    code = models.CharField(
        max_length=50,
        unique=True,
        validators=[validate_cancellation_reason_code],
        verbose_name=_("Code"),
        help_text=_(
            "Free-form code, ^[A-Z_]+$. StandardCancellationReason is only the "
            "source of default seed data (see apps/bookings/signals.py)."
        ),
    )
    description = models.CharField(max_length=255, verbose_name=_("Description"))

    class Meta:
        verbose_name = _("Cancellation Reason")
        verbose_name_plural = _("Cancellation Reasons")

    def __str__(self):
        return self.description
