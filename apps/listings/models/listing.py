from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F
from django.utils.translation import gettext_lazy as _

from apps.listings.choices import (
    ListingStatus,
    ListingType,
    MaxGuestsChoices,
    MealType,
    RentalType,
)
from core.models import BaseModel, TimePolicy


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
        "listings.Address",
        on_delete=models.PROTECT,
        related_name="listing",
        verbose_name=_("Address"),
    )

    max_guests = models.PositiveIntegerField(
        choices=MaxGuestsChoices, verbose_name=_("Maximum Guests")
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
        "listings.Amenity",
        through="listings.ListingAmenity",
        blank=True,
        related_name="listings",
        verbose_name=_("Amenities"),
    )

    class Meta:
        verbose_name = _("Listing")
        verbose_name_plural = _("Listings")
        ordering = ["-created_at"]
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
        self._validate_rooms_count_only_for_apartment()

    def _validate_rooms_count_only_for_apartment(self):
        if self.type != ListingType.APARTMENT and self.rooms_count:
            raise ValidationError(
                {"rooms_count": _("rooms_count is only applicable to type=apartment.")}
            )

    # Counters do not trigger full model validation on every view.
    def increment_views_count(self):
        Listing.objects.filter(pk=self.pk).update(views_count=F("views_count") + 1)

    @property
    def is_visible_to_public(self) -> bool:
        """Publicly visible announcement."""
        return self.status == ListingStatus.PUBLISHED and self.is_active
