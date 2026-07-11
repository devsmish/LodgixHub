import uuid
from datetime import time

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class SoftDeleteQuerySet(models.QuerySet):
    """
    A custom QuerySet that ensures bulk operations (e.g., .delete()) perform a soft delete
    instead of a physical deletion from the database.
    """

    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def dead(self):
        return self.filter(deleted_at__isnull=False)

    def delete(self):
        now = timezone.now()
        return self.update(deleted_at=now, updated_at=now)

    def hard_delete(self):
        return super().delete()

    def restore(self):
        return self.update(deleted_at=None, updated_at=timezone.now())


class SoftDeleteManager(models.Manager):
    """
    A default manager that automatically hides logically deleted records.
    """

    def get_queryset(self) -> SoftDeleteQuerySet:
        return SoftDeleteQuerySet(self.model, using=self._db).alive()


class BaseModel(models.Model):
    """
    An abstract base model. It provides a UUID primary key,
    creation/update timestamps, and robust soft delete functionality.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    @property
    def is_deleted(self):
        return self.deleted_at is not None

    def delete(self, using=None, keep_parents=False):
        """Single logical deletion of an object."""
        now = timezone.now()
        type(self).all_objects.filter(pk=self.pk).update(deleted_at=now, updated_at=now)
        self.deleted_at = now
        self.updated_at = now

    def hard_delete(self, using=None, keep_parents=False):
        """Physical deletion of an object from the database."""
        super().delete(using=using, keep_parents=keep_parents)

    def restore(self, using=None):
        """Restoring a logically deleted record."""
        now = timezone.now()
        type(self).all_objects.filter(pk=self.pk).update(
            deleted_at=None, updated_at=now
        )
        self.deleted_at = None
        self.updated_at = now


class TimestampedModel(models.Model):
    """
    An abstract model for entities that can be modified but not deleted
    (e.g., Listings, Bookings). Contains a UUID and timestamps.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class LogQuerySet(models.QuerySet):

    def update(self, *args, **kwargs):
        raise ValidationError("Bulk updates are not allowed for logs.")

    def bulk_update(self, *args, **kwargs):
        raise ValidationError("Bulk updates are not allowed for logs.")

    def delete(self):
        raise ValidationError("Bulk deletes are not allowed for logs.")

    def purge(self):
        return super().delete()


class LogManager(models.Manager):
    def get_queryset(self) -> LogQuerySet:
        return LogQuerySet(self.model, using=self._db)


class LogModel(models.Model):
    """
    An abstract model for append-only logs (PriceHistory, SearchHistory,
    ViewHistory, NotificationLog).
    Disallows updates to existing rows to ensure data integrity.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = LogManager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Log entries are immutable and cannot be updated.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(
            "Log entries are protected against deletion and cannot be physically erased."
        )

    def hard_delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)


class TimePolicy(models.Model):
    check_in_time = models.TimeField(
        default=time(14, 0), verbose_name=_("Check-in time")
    )
    check_out_time = models.TimeField(
        default=time(11, 0), verbose_name=_("Check-out time")
    )

    class Meta:
        abstract = True
