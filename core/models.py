import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    """
    A custom QuerySet that ensures bulk operations (e.g., .delete()) perform a soft delete instead
    of a physical deletion from the database.
    """

    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def dead(self):
        return self.filter(deleted_at__isnull=False)

    def delete(self):
        return self.update(deleted_at=timezone.now())

    def hard_delete(self):
        return super().delete()

    def restore(self):
        return self.update(deleted_at=None)


class SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    """
    A default manager that automatically hides logically deleted records.
    """

    def get_queryset(self):
        return super().get_queryset().alive()


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

    def delete(self, using=None, keep_parents=False):
        """Single logical deletion of an object."""
        self.deleted_at = timezone.now()
        self.save(using=using, update_fields=["deleted_at", "updated_at"])

    def hard_delete(self, using=None, keep_parents=False):
        """Physical deletion of an object from the database."""
        super().delete(using=using, keep_parents=keep_parents)

    def restore(self, using=None):
        """Restoring a logically deleted record."""
        self.deleted_at = None
        self.save(using=using, update_fields=["deleted_at", "updated_at"])


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


class LogModel(models.Model):
    """
    An abstract model for append-only logs (PriceHistory).
    Disallows updates to existing rows to ensure data integrity.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError(
                "Log entries are immutable and cannot be updated."
            )
        super().save(*args, **kwargs)
