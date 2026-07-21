from django.apps import AppConfig


class SecurityConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.security"
    verbose_name = "Security"

    def ready(self):
        from apps.security import schema  # noqa: F401 — регистрирует CustomJWTAuthentication в drf-spectacular
