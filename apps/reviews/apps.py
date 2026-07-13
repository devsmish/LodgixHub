from django.apps import AppConfig


class ReviewsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.reviews"
    verbose_name = "Reviews"

    def ready(self):
        """
        Updating reviews_count in listings.
        Standard post_save/post_delete signals are registered simply by importing
        the module containing the @receiver.
        """
        from apps.reviews import signals
