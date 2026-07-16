from apps.listings.models import Room


class RoomRepository:

    @staticmethod
    def get_for_listing(listing_id):
        return Room.objects.filter(listing_id=listing_id)

    @staticmethod
    def get_by_id_for_listing(listing_id, room_id):
        return Room.all_objects.filter(listing_id=listing_id, id=room_id).first()
