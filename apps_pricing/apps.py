from django.apps import AppConfig


class PricingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"  # CHANGED: было DEFAULT_AUTO_FIELD — Django не читает
    name = "apps.pricing"
    verbose_name = "Pricing"  # NEW
