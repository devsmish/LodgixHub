from django.contrib.auth.models import BaseUserManager

from core.models import SoftDeleteQuerySet


class CustomUserManager(BaseUserManager):
    """
    User manager with support for email-based authentication and soft delete.
    """

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).alive()

    def _create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The email field must be filled in.")

        email = self.normalize_email(email).lower().strip()
        extra_fields.setdefault("is_active", True)

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if not extra_fields.get("is_staff"):
            raise ValueError("Superuser must have is_staff=True.")
        if not extra_fields.get("is_superuser"):
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)
