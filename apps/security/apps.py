from django.apps import AppConfig


class SecurityConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.security"
    verbose_name = "Security"

    def ready(self):
        # registers CustomJWTAuthentication in drf-spectacular
        from apps.security import (  # noqa: F401
            schema,
        )
