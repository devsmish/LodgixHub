from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import CheckConstraint, Q

from core.models import TimestampedModel


class Photo(TimestampedModel):
    image = models.ImageField(upload_to="listings/photos/")
    caption = models.CharField(max_length=255, blank=True)

    # ForeignKey должны быть null=True, так как связь XOR
    listing = models.ForeignKey(
        "listings.Listing", on_delete=models.CASCADE, null=True, blank=True
    )
    room = models.ForeignKey(
        "listings.Room", on_delete=models.CASCADE, null=True, blank=True
    )

    class Meta:
        # Индекс для ускорения запросов
        indexes = [
            models.Index(fields=["listing"]),
            models.Index(fields=["room"]),
        ]
        # Ограничение на уровне БД: XOR связь
        constraints = [
            CheckConstraint(
                check=(
                    Q(listing__isnull=False, room__isnull=True)
                    | Q(listing__isnull=True, room__isnull=False)
                ),
                name="photo_xor_listing_or_room",
            )
        ]

    def clean(self):
        # Валидация для админки/форм
        if (self.listing and self.room) or (not self.listing and not self.room):
            raise ValidationError(
                "Фотография должна принадлежать либо Листингу, либо Комнате, но не обоим сразу и не ничему."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
