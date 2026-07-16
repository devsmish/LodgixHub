from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import TimestampedModel


class ListingAmenity(TimestampedModel):

    listing = models.ForeignKey(
        "listings.Listing", on_delete=models.CASCADE, related_name="listing_amenities"
    )
    amenity = models.ForeignKey(
        "listings.Amenity", on_delete=models.CASCADE, related_name="amenity_listings"
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
