from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.exceptions import ValidationError as DRFValidationError


class ListingNotBookableError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = (
        "The listing is not available for booking (it is unpublished, "
        "hidden, or a price has not yet been set)."
    )
    default_code = "listing_not_bookable"


class BookingNotAvailableError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "The selected dates are already booked."
    default_code = "booking_not_available"


class BookingTransitionNotAllowedError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid booking status transition."
    default_code = "booking_transition_not_allowed"


class BookingCancelWindowExpiredError(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = (
        "The free cancellation period has expired (less than 24 hours before check-in). "
        "Contact the owner or support."
    )
    default_code = "booking_cancel_window_expired"


class CancellationReasonRequiredError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "If the owner cancels a booking, they must specify the reason."
    default_code = "cancellation_reason_required"


def convert_django_validation_error(exc: DjangoValidationError) -> DRFValidationError:
    """Translates `django.core.exceptions.ValidationError` into a
    proper DRF response (400) instead of an unhandled 500 error."""
    detail = (
        exc.message_dict if hasattr(exc, "message_dict") else {"detail": exc.messages}
    )
    return DRFValidationError(detail)
