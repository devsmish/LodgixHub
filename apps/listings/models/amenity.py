from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.listings.choices import AmenityGroup, StandardAmenity
from core.models import BaseModel

amenity_slug_validator = RegexValidator(
    regex=r"^[a-z0-9_]+$",
    message=_(
        "The slug may contain only lowercase Latin letters, digits, and underscores."
    ),
)


class Amenity(BaseModel):
    name = models.CharField(max_length=100, verbose_name=_("Name"))
    slug = models.CharField(
        max_length=50,
        unique=True,
        validators=[amenity_slug_validator],
        verbose_name=_("System Key"),
        help_text=_(
            "Free-form unique key (e.g. 'sauna'). StandardAmenity only seeds "
            "the initial well-known set — it does not restrict new values."
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
