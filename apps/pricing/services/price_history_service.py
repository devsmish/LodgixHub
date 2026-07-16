from django.core.exceptions import ValidationError as DjangoValidationError

from apps.pricing.errors import PriceHistoryValidationError
from apps.pricing.models import PriceHistory
from apps.pricing.repositories import PriceHistoryRepository


class PriceHistoryService:

    def __init__(self, repository: PriceHistoryRepository = None):
        self.repository = repository or PriceHistoryRepository()

    def set_price_for_listing(
        self, *, listing, changed_by, price, valid_from, currency="EUR"
    ):
        instance = PriceHistory(
            listing=listing,
            price=price,
            valid_from=valid_from,
            currency=currency,
            changed_by=changed_by,
        )
        return self._save_or_raise(instance)

    def set_price_for_room(
        self, *, room, changed_by, price, valid_from, currency="EUR"
    ):
        instance = PriceHistory(
            room=room,
            price=price,
            valid_from=valid_from,
            currency=currency,
            changed_by=changed_by,
        )
        return self._save_or_raise(instance)

    @staticmethod
    def _save_or_raise(instance):
        """Translates a Django ValidationError into a correct DRF response."""
        try:
            instance.save()
        except DjangoValidationError as exc:
            raise PriceHistoryValidationError(_django_error_to_dict(exc)) from exc
        return instance

    def get_history_for_listing(self, listing_id):
        return self.repository.get_for_listing(listing_id)

    def get_history_for_room(self, room_id):
        return self.repository.get_for_room(room_id)


def _django_error_to_dict(exc: DjangoValidationError):
    if hasattr(exc, "message_dict"):
        return exc.message_dict
    return {"detail": exc.messages}
