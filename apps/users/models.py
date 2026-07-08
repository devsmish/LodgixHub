import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.users.choices import BlockedReason
from apps.users.managers import CustomUserManager


class User(AbstractBaseUser, PermissionsMixin):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, verbose_name="Email address")

    # Personal data
    first_name = models.CharField(max_length=150, blank=True, verbose_name="Name")
    last_name = models.CharField(max_length=150, blank=True, verbose_name="Surname")
    nickname = models.CharField(
        max_length=150, unique=True, null=True, blank=True, verbose_name="Username"
    )
    phone = models.CharField(
        max_length=30, null=True, blank=True, verbose_name="Phone number"
    )
    contact_phone = models.CharField(
        max_length=30, null=True, blank=True, verbose_name="Contact phone"
    )
    avatar = models.ImageField(
        upload_to="avatars/", null=True, blank=True, verbose_name="Avatar"
    )

    # System statuses and technical flags
    is_active = models.BooleanField(default=True, verbose_name="Active")
    is_staff = models.BooleanField(default=False, verbose_name="Employee status")
    is_superuser = models.BooleanField(default=False, verbose_name="Superuser status")
    token_version = models.PositiveIntegerField(default=1, verbose_name="Token version")

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

    def __str__(self):
        return self.email

    def delete(self, using=None, keep_parents=False):
        self.is_active = False
        self.deleted_at = timezone.now()
        self.save(using=using, update_fields=["is_active", "deleted_at", "updated_at"])

    def restore(self, using=None):
        self.is_active = True
        self.deleted_at = None
        self.save(using=using, update_fields=["is_active", "deleted_at", "updated_at"])

    @property
    def is_deleted(self):
        return self.deleted_at is not None
