from apps.pricing.models import PriceHistory


class PriceHistoryRepository:

    @staticmethod
    def get_for_listing(listing_id):
        return PriceHistory.objects.filter(listing_id=listing_id)

    @staticmethod
    def get_for_room(room_id):
        return PriceHistory.objects.filter(room_id=room_id)
