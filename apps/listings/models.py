from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.listings.choices import (
    AmenityGroup,
    ListingStatus,
    ListingType,
    MealType,
    RentalType,
    RoomType,
    StandardAmenity,
)
from core.models import BaseModel, TimestampedModel, TimePolicy


class Amenity(models.Model):
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


class Listing(TimestampedModel, TimePolicy):
    """
    Core Property asset. Inherits from TimestampedModel (non-deletable).
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="listings",
        verbose_name=_("Owner"),
    )
    title = models.CharField(max_length=255, verbose_name=_("Title"))
    description = models.TextField(blank=True, verbose_name=_("Description"))

    type = models.CharField(
        max_length=20,
        choices=ListingType,
        default=ListingType.APARTMENT,
        verbose_name=_("Property Type"),
    )
    status = models.CharField(
        max_length=20,
        choices=ListingStatus,
        default=ListingStatus.DRAFT,
        verbose_name=_("Status"),
    )

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[
            MinValueValidator(Decimal("-90.0")),
            MaxValueValidator(Decimal("90.0")),
        ],
        verbose_name=_("Latitude"),
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[
            MinValueValidator(Decimal("-180.0")),
            MaxValueValidator(Decimal("180.0")),
        ],
        verbose_name=_("Longitude"),
    )

    max_guests = models.PositiveIntegerField(
        validators=[MinValueValidator(1)], verbose_name=_("Maximum Guests")
    )

    price_per_night = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name=_("Price Per Night"),
    )
    rental_type = models.CharField(
        max_length=20,
        choices=RentalType,
        default=RentalType.ANY,
        verbose_name=_("Rental Type"),
    )
    meal_type = models.CharField(
        max_length=20,
        choices=MealType,
        default=MealType.NONE,
        verbose_name=_("Meal Type"),
    )

    amenities = models.ManyToManyField(
        Amenity, blank=True, related_name="listings", verbose_name=_("Amenities")
    )

    class Meta:
        verbose_name = _("Listing")
        verbose_name_plural = _("Listings")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(latitude__gte=-90) & models.Q(latitude__lte=90),
                name="listing_latitude_range",
            ),
            models.CheckConstraint(
                condition=models.Q(longitude__gte=-180) & models.Q(longitude__lte=180),
                name="listing_longitude_range",
            ),
            models.CheckConstraint(
                condition=models.Q(max_guests__gte=1), name="listing_max_guests_minimum"
            ),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_type_display()})"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Room(BaseModel, TimePolicy):
    """
    Room asset for multi-unit properties (Hotels/Hostels). Inherits from BaseModel (supports soft delete).
    """

    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="rooms",
        verbose_name=_("Listing"),
    )
    room_type = models.CharField(
        max_length=20,
        choices=RoomType,
        default=RoomType.SINGLE,
        verbose_name=_("Room Type"),
    )
    name = models.CharField(
        max_length=100, blank=True, verbose_name=_("Room Name/Number")
    )

    max_guests = models.PositiveIntegerField(
        validators=[MinValueValidator(1)], verbose_name=_("Maximum Guests")
    )

    class Meta:
        verbose_name = _("Room")
        verbose_name_plural = _("Rooms")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(max_guests__gte=1), name="room_max_guests_minimum"
            ),
        ]

    def __str__(self):
        return f"{self.get_room_type_display()} in {self.listing.title}"

    def clean(self):
        super().clean()
        if self.listing_id and self.listing.type == ListingType.APARTMENT:
            raise ValidationError(
                {
                    "listing": _(
                        "Cannot attach individual rooms to an APARTMENT listing type."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
