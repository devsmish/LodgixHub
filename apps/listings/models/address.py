from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import TimestampedModel


class Address(TimestampedModel):

    country = models.CharField(
        max_length=100, default="Germany", verbose_name=_("Country")
    )
    region = models.CharField(max_length=100, verbose_name=_("Region (Bundesland)"))
    city = models.CharField(max_length=100, verbose_name=_("City"))
    district = models.CharField(
        max_length=100, blank=True, null=True, verbose_name=_("District")
    )
    street = models.CharField(max_length=255, verbose_name=_("Street"))
    house_number = models.CharField(max_length=20, verbose_name=_("House Number"))
    postal_code = models.CharField(max_length=10, verbose_name=_("Postal Code"))

    floor = models.SmallIntegerField(blank=True, null=True, verbose_name=_("Floor"))
    apartment_number = models.CharField(
        max_length=10, blank=True, null=True, verbose_name=_("Apartment Number")
    )

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        validators=[
            MinValueValidator(Decimal("-90.0")),
            MaxValueValidator(Decimal("90.0")),
        ],
        verbose_name=_("Latitude"),
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        validators=[
            MinValueValidator(Decimal("-180.0")),
            MaxValueValidator(Decimal("180.0")),
        ],
        verbose_name=_("Longitude"),
    )

    class Meta:
        verbose_name = _("Address")
        verbose_name_plural = _("Addresses")
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(latitude__isnull=True)
                    | (models.Q(latitude__gte=-90) & models.Q(latitude__lte=90))
                ),
                name="address_latitude_range",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(longitude__isnull=True)
                    | (models.Q(longitude__gte=-180) & models.Q(longitude__lte=180))
                ),
                name="address_longitude_range",
            ),
        ]

    def __str__(self):
        return f"{self.city}, {self.street} {self.house_number}"
