from django.apps import AppConfig
from django.db.models.signals import post_migrate


class ListingsConfig(AppConfig):
    DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
    name = "apps.listings"

    def ready(self):

        from apps.listings.signals import create_standard_amenities

        post_migrate.connect(create_standard_amenities, sender=self)
