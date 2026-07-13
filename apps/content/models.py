import os
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.db.models.constraints import CheckConstraint
from django.utils.translation import gettext_lazy as _

from apps.content.constants import MAX_PHOTOS_PER_LISTING
from core.models import TimestampedModel
from core.validators import validate_image


def photo_upload_path(instance, filename):
    ext = filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"

    if instance.listing_id:
        folder_path = os.path.join("listings", str(instance.listing_id), "photos")
    else:
        folder_path = os.path.join("rooms", str(instance.room_id), "photos")

    if settings.DEFAULT_FILE_STORAGE == "django.core.files.storage.FileSystemStorage":
        full_path = os.path.join(settings.MEDIA_ROOT, folder_path)
        if not os.path.exists(full_path):
            os.makedirs(full_path, exist_ok=True)

    return os.path.join(folder_path, filename)


class Photo(TimestampedModel):

    image = models.ImageField(
        upload_to=photo_upload_path,
        validators=[validate_image],
        verbose_name=_("Image"),
    )
    caption = models.CharField(
        max_length=255, blank=True, null=True, verbose_name=_("Caption")
    )
    is_primary = models.BooleanField(default=False, verbose_name=_("Is primary"))
    order = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_("Display order"),
    )

    listing = models.ForeignKey(
        "listings.Listing", on_delete=models.CASCADE, null=True, blank=True
    )
    room = models.ForeignKey(
        "listings.Room", on_delete=models.CASCADE, null=True, blank=True
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_photos",
        verbose_name=_("Uploaded by"),
    )

    class Meta:
        ordering = ["order", "created_at"]
        indexes = [
            models.Index(fields=["listing", "order"], name="idx_photo_listing"),
            models.Index(fields=["room", "order"], name="idx_photo_room"),
        ]
        constraints = [
            CheckConstraint(
                condition=Q(listing__isnull=False, room__isnull=True)
                | Q(listing__isnull=True, room__isnull=False),
                name="photo_xor_listing_or_room",
            )
        ]

    def clean(self):
        if (self.listing and self.room) or (not self.listing and not self.room):
            raise ValidationError(
                _(
                    "The photo must belong to either a Listing or a Room, "
                    "but not to both simultaneously, and not to neither."
                )
            )

        if not self.pk:
            target_filter = (
                {"listing": self.listing} if self.listing else {"room": self.room}
            )
            existing_count = Photo.objects.filter(**target_filter).count()
            if existing_count >= MAX_PHOTOS_PER_LISTING:
                raise ValidationError(
                    _("Maximum of %(max)s photos allowed per gallery.")
                    % {"max": MAX_PHOTOS_PER_LISTING}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        target = self.listing_id or self.room_id
        return f"Photo {self.id} for {target}"
