from apps.content.models import Photo


class PhotoRepository:

    @staticmethod
    def get_for_listing(listing_id):
        return Photo.objects.filter(listing_id=listing_id)

    @staticmethod
    def get_by_id_for_listing(listing_id, photo_id):
        return Photo.objects.filter(listing_id=listing_id, id=photo_id).first()
