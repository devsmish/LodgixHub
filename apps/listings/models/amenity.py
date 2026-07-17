from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.listings.choices import AmenityGroup, StandardAmenity
from core.models import BaseModel


class Amenity(BaseModel):
    name = models.CharField(max_length=100, verbose_name=_("Name"))
    slug = models.CharField(
        max_length=50,
        unique=True,
        choices=StandardAmenity,
        verbose_name=_("System Key"),
    )
    group = models.CharField(
        max_length=50,
        blank=True,
        choices=AmenityGroup,
        default=AmenityGroup.BASIC,
        verbose_name=_("Category Group"),
    )
    icon = models.CharField(
        max_length=50, blank=True, null=True, verbose_name=_("Icon Name")
    )

    class Meta:
        verbose_name = _("Amenity")
        verbose_name_plural = _("Amenities")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.slug:
            self.group = StandardAmenity.get_group_for_slug(self.slug)
        super().save(*args, **kwargs)
