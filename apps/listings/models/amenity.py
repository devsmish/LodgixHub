from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.listings.choices import AmenityGroup, StandardAmenity
from core.models import BaseModel

validate_amenity_slug = RegexValidator(
    regex=r"^[a-z][a-z0-9_]*$",
    message=_(
        "Slug must be lowercase snake_case: start with a letter, "
        "only lowercase letters, digits and underscores."
    ),
)


class Amenity(BaseModel):
    name = models.CharField(max_length=100, verbose_name=_("Name"))
    slug = models.CharField(
        max_length=50,
        unique=True,
        validators=[validate_amenity_slug],
        verbose_name=_("System Key"),
        help_text=_(
            "Free-form system key, lowercase snake_case. StandardAmenity is only "
            "the source of default seed data (see apps/listings/signals.py), "
            "not a closed set — new amenities are not restricted to it."
        ),
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
