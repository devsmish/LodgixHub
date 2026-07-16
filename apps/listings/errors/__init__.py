from rest_framework import status
from rest_framework.exceptions import APIException


class ListingTypeImmutableError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Тип объявления (type) нельзя изменить после создания."
    default_code = "listing_type_immutable"


class ListingStatusTransitionNotAllowedError(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "У вас нет прав на этот переход статуса объявления."
    default_code = "listing_status_transition_not_allowed"


class ListingHasActiveBookingsError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = (
        "Объявление нельзя удалить: есть бронь в статусе pending/confirmed."
    )
    default_code = "listing_has_active_bookings"


class RoomHasActiveBookingsError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Комнату нельзя удалить: есть бронь в статусе pending/confirmed."
    default_code = "room_has_active_bookings"


class RoomNotAllowedForApartmentError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Нельзя добавлять комнаты к объявлению типа apartment."
    default_code = "room_not_allowed_for_apartment"
