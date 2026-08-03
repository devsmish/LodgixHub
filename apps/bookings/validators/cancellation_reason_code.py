from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

validate_cancellation_reason_code = RegexValidator(
    regex=r"^[A-Z_]+$",
    message=_("Code must contain only uppercase letters and underscores."),
)
