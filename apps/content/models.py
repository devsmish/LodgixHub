import os
import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.constraints import CheckConstraint

from config import settings
from core.models import TimestampedModel


def photo_upload_path(instance, filename):
    # We generate a unique filename to avoid collisions.
    ext = filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"

    if instance.listing:
        folder_path = os.path.join("listings", str(instance.listing.id), "photos")
    else:
        folder_path = os.path.join("rooms", str(instance.room.id), "photos")

    if settings.DEFAULT_FILE_STORAGE == "django.core.files.storage.FileSystemStorage":
        full_path = os.path.join(settings.MEDIA_ROOT, folder_path)
        if not os.path.exists(full_path):
            os.makedirs(full_path, exist_ok=True)

    return os.path.join(folder_path, filename)


class Photo(TimestampedModel):
    image = models.ImageField(upload_to=photo_upload_path)
    caption = models.CharField(max_length=255, blank=True)

    # ForeignKeys must have `null=True` because of the XOR relationship.
    listing = models.ForeignKey(
        "listings.Listing", on_delete=models.CASCADE, null=True, blank=True
    )
    room = models.ForeignKey(
        "listings.Room", on_delete=models.CASCADE, null=True, blank=True
    )

    class Meta:
        indexes = [
            models.Index(fields=["listing"], name="idx_photo_listing"),
            models.Index(fields=["room"], name="idx_photo_room"),
        ]
        # Database-level constraint: XOR relationship
        constraints = [
            CheckConstraint(
                condition=Q(listing__isnull=False, room__isnull=True)
                | Q(listing__isnull=True, room__isnull=False),
                name="photo_xor_listing_or_room",
            )
        ]

    def clean(self):
        # Validation for the admin panel
        if (self.listing and self.room) or (not self.listing and not self.room):
            raise ValidationError(
                """The photograph must belong to either a Listing or a Room, 
                but not to both simultaneously, and not to neither."""
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
