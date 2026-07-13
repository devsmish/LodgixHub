from django.apps import AppConfig
from django.db.models.signals import post_migrate


class BookingsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.bookings"
    verbose_name = "Bookings"

    def ready(self):
        from apps.bookings.signals import create_standard_cancellation_reasons

        post_migrate.connect(create_standard_cancellation_reasons, sender=self)
