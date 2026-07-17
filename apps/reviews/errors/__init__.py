from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.exceptions import ValidationError as DRFValidationError


class ReviewAlreadyExistsError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "A review for this booking has already been submitted."  # booking — OneToOneField
    default_code = "review_already_exists"


def convert_django_validation_error(exc: DjangoValidationError) -> DRFValidationError:
    """Translates django.core.exceptions.ValidationError (from Review.full_clean())
    into a proper DRF response (400) instead of an unhandled 500."""
    detail = (
        exc.message_dict if hasattr(exc, "message_dict") else {"detail": exc.messages}
    )
    return DRFValidationError(detail)
