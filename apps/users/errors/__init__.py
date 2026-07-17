from rest_framework import status
from rest_framework.exceptions import APIException


class UserHasActiveBookingsError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = (
        "Action not possible: "
        "the user has active bookings (with 'pending' or 'confirmed' status) "
        "as either a renter or a landlord. "
        "First, close these bookings or wait for them to be completed."
    )
    default_code = "user_has_active_bookings"


class UserAlreadyBlockedError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "The user is already blocked."
    default_code = "user_already_blocked"


class UserNotBlockedError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "The user is not blocked."
    default_code = "user_not_blocked"


class PublicProfileNotAccessibleError(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = (
        "The public profile is available only if there is an active "
        "or completed booking for this user's listing."
    )
    default_code = "public_profile_not_accessible"
