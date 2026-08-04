from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

cancellation_reason_code_validator = RegexValidator(
    regex=r"^[A-Z_]+$",
    message=_("The code may contain only uppercase Latin letters and underscores."),
)
