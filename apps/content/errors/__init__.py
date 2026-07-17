from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError


def convert_django_validation_error(exc: DjangoValidationError) -> DRFValidationError:
    """Translates `django.core.exceptions.ValidationError` (from `Photo.full_clean()`:
    XOR `listing`/`room`, `MAX_PHOTOS_PER_LISTING` limit) into a proper
    DRF response (400) instead of an unhandled 500 error."""
    detail = (
        exc.message_dict if hasattr(exc, "message_dict") else {"detail": exc.messages}
    )
    return DRFValidationError(detail)
