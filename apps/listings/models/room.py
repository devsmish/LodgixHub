from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.listings.choices import ListingType, MaxGuestsChoices, RoomType
from core.models import BaseModel, TimePolicy


class Room(BaseModel, TimePolicy):
    """
    Room asset for multi-unit properties (Hotels/Hostels).
    Inherits from BaseModel (supports soft delete).
    """

    listing = models.ForeignKey(
        "listings.Listing",
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
        choices=MaxGuestsChoices, verbose_name=_("Maximum Guests")
    )

    rooms_available_count = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(500)],
        verbose_name=_("Available rooms of this category"),
    )

    class Meta:
        verbose_name = _("Room")
        verbose_name_plural = _("Rooms")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(max_guests__gte=1), name="room_max_guests_minimum"
            ),
            models.CheckConstraint(
                condition=models.Q(rooms_available_count__gte=1),
                name="room_available_count_minimum",
            ),
        ]

    def __str__(self):
        return f"{self.get_room_type_display()} in {self.listing.title}"

    def clean(self):
        super().clean()
        self._validate_listing_supports_rooms()

    def _validate_listing_supports_rooms(self):
        """Rooms can only be linked to a hotel or hostel, not an apartment."""
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
