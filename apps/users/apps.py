from django.apps import AppConfig
from django.db.models.signals import post_migrate


class UsersConfig(AppConfig):
    DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
    name = "apps.users"
    verbose_name = "Users"

    def ready(self):
        from apps.users.signals import create_system_groups

        # Execution of the function is tied to the completion of the migration.
        post_migrate.connect(create_system_groups, sender=self)
