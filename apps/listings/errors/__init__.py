from rest_framework import status
from rest_framework.exceptions import APIException


class ListingTypeImmutableError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "The ad type (type) cannot be changed after creation."
    default_code = "listing_type_immutable"


class ListingStatusTransitionNotAllowedError(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You do not have permission to perform this ad status transition."
    default_code = "listing_status_transition_not_allowed"


class ListingHasActiveBookingsError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "The listing cannot be deleted: there is a booking with a status of pending/confirmed."
    default_code = "listing_has_active_bookings"


class RoomHasActiveBookingsError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "The room cannot be deleted: there is a booking with a status of pending/confirmed."
    default_code = "room_has_active_bookings"


class RoomNotAllowedForApartmentError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "You cannot add rooms to an 'apartment' type listing."
    default_code = "room_not_allowed_for_apartment"
