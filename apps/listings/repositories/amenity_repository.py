from apps.listings.models import Amenity


class AmenityRepository:

    @staticmethod
    def get_active_queryset():
        return Amenity.objects.all()

    @staticmethod
    def get_all_queryset():
        return Amenity.all_objects.all()
