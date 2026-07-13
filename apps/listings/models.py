from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F
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
from core.models import BaseModel, TimePolicy, TimestampedModel


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


class Listing(BaseModel, TimePolicy):
    """
    Core Property asset. Inherits from BaseModel (soft delete +
    prohibition on deletion while a reservation is active).
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

    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))

    address = models.OneToOneField(
        Address,
        on_delete=models.PROTECT,
        related_name="listing",
        verbose_name=_("Address"),
    )

    max_guests = models.PositiveIntegerField(
        validators=[MinValueValidator(1)], verbose_name=_("Maximum Guests")
    )

    rooms_count = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("Rooms Count"),
        help_text=_("Used for type=apartment; not applicable to hotel/hostel."),
    )

    current_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name=_("Current Price (cached from PriceHistory)"),
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

    deposit_required = models.BooleanField(
        default=False, verbose_name=_("Deposit Required")
    )
    deposit_percent = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_("Deposit Percent"),
    )
    deposit_refundable = models.BooleanField(
        default=False, verbose_name=_("Deposit Refundable")
    )

    views_count = models.PositiveIntegerField(default=0, verbose_name=_("Views Count"))
    rating_avg = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("Average Rating"),
        help_text=_("Denormalized, recalculated by signal on Review change."),
    )
    reviews_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Reviews Count"),
        help_text=_("Denormalized, recalculated by signal on Review change."),
    )

    amenities = models.ManyToManyField(
        Amenity,
        through="ListingAmenity",
        blank=True,
        related_name="listings",
        verbose_name=_("Amenities"),
    )

    class Meta:
        verbose_name = _("Listing")
        verbose_name_plural = _("Listings")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(max_guests__gte=1), name="listing_max_guests_minimum"
            ),
            models.CheckConstraint(
                condition=models.Q(deposit_percent__gte=0)
                & models.Q(deposit_percent__lte=100),
                name="listing_deposit_percent_range",
            ),
        ]
        indexes = [
            models.Index(fields=["-views_count"]),
            models.Index(fields=["-reviews_count"]),
            models.Index(fields=["type", "status", "is_active"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_type_display()})"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.type != ListingType.APARTMENT and self.rooms_count:
            raise ValidationError(
                {"rooms_count": _("rooms_count is only applicable to type=apartment.")}
            )

    # Counters do not trigger full model validation on every view.
    def increment_views_count(self):
        Listing.objects.filter(pk=self.pk).update(views_count=F("views_count") + 1)


class ListingAmenity(TimestampedModel):

    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="listing_amenities"
    )
    amenity = models.ForeignKey(
        Amenity, on_delete=models.CASCADE, related_name="amenity_listings"
    )

    class Meta:
        verbose_name = _("Listing Amenity")
        verbose_name_plural = _("Listing Amenities")
        constraints = [
            models.UniqueConstraint(
                fields=["listing", "amenity"], name="unique_listing_amenity"
            ),
        ]

    def __str__(self):
        return f"{self.listing_id} — {self.amenity_id}"


class Room(BaseModel, TimePolicy):
    """
    Room asset for multi-unit properties (Hotels/Hostels).
    Inherits from BaseModel (supports soft delete).
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
