import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.users.choices import BlockedReason, GenderChoices
from apps.users.managers import CustomUserManager
from core.validators import (
    name_validator,
    nickname_validator,
    phone_validator,
    validate_custom_email,
    validate_image,
)


class User(AbstractBaseUser, PermissionsMixin):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(
        max_length=254,
        unique=True,
        validators=[validate_custom_email],
        verbose_name="Email address",
    )

    # Personal data
    first_name = models.CharField(
        max_length=150, blank=True, validators=[name_validator], verbose_name="Name"
    )
    last_name = models.CharField(
        max_length=150, blank=True, validators=[name_validator], verbose_name="Surname"
    )
    nickname = models.CharField(
        max_length=150,
        unique=True,
        null=True,
        blank=True,
        verbose_name="Username",
        validators=[nickname_validator],
    )
    birth_date = models.DateField(null=True, blank=True, verbose_name="Birth date")
    gender = models.CharField(
        max_length=1,
        choices=GenderChoices,
        null=True,
        blank=True,
        verbose_name="Gender",
        help_text="Optional field. M – Male, F – Female, X – Other.",
    )
    phone = models.CharField(
        max_length=30,
        null=True,
        blank=True,
        verbose_name="Phone number",
        validators=[phone_validator],
    )
    contact_phone = models.CharField(
        max_length=30,
        null=True,
        blank=True,
        verbose_name="Contact phone",
        validators=[phone_validator],
    )
    avatar = models.ImageField(
        upload_to="avatars/",
        null=True,
        blank=True,
        verbose_name="Avatar",
        validators=[validate_image],
    )

    # System statuses and technical flags
    is_active = models.BooleanField(default=True, verbose_name="Active")
    is_staff = models.BooleanField(default=False, verbose_name="Employee status")
    is_superuser = models.BooleanField(default=False, verbose_name="Superuser status")
    token_version = models.PositiveIntegerField(default=0, verbose_name="Token version")

    # Lock Audit
    blocked_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Blocking date"
    )
    blocked_reason = models.CharField(
        max_length=50,
        choices=BlockedReason,
        null=True,
        blank=True,
        verbose_name="Reason for blocking",
    )
    blocked_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="blocked_users",
        verbose_name="Blocked by whom",
    )

    # Settings and consents
    notify_by_email = models.BooleanField(
        default=True, verbose_name="Email notifications"
    )
    terms_accepted_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Date of adoption of the agreement"
    )

    # Lifecycle timestamps
    date_joined = models.DateTimeField(
        default=timezone.now, verbose_name="Registration date"
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Last updated")
    deleted_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Logical deletion date"
    )

    objects = CustomUserManager()
    all_objects = models.Manager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-date_joined"]
        base_manager_name = "all_objects"

    def __str__(self):
        return self.email

    def clean(self):
        super().clean()
        if self.email:
            self.email = self.email.lower()

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower().strip()
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.is_active = False
        self.save(using=using, update_fields=["deleted_at", "is_active", "updated_at"])

    def restore(self, using=None):
        self.deleted_at = None
        self.is_active = True
        self.blocked_at = None
        self.blocked_reason = None
        self.blocked_by = None
        self.save(
            using=using,
            update_fields=[
                "deleted_at",
                "is_active",
                "blocked_at",
                "blocked_reason",
                "blocked_by",
                "updated_at",
            ],
        )

    @property
    def is_deleted(self):
        return self.deleted_at is not None
