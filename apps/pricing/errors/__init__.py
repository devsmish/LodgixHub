from rest_framework import status
from rest_framework.exceptions import APIException


class PriceHistoryValidationError(APIException):
    """Wraps django.core.exceptions.ValidationError from PriceHistory.clean()"""

    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "price_history_invalid"
