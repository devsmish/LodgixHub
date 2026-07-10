from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import CheckConstraint, Q
from django.utils import timezone

from core.models import LogModel


class PriceHistory(LogModel):
    # XOR: use CheckConstraint for DB
    listing = models.ForeignKey(
        "listings.Listing", on_delete=models.CASCADE, null=True, blank=True
    )
    room = models.ForeignKey(
        "listings.Room", on_delete=models.CASCADE, null=True, blank=True
    )

    price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="EUR")
    effective_date = models.DateField(default=timezone.now)

    class Meta:
        # Uniqueness: object + date = one record
        unique_together = ("listing", "room", "effective_date")
        ordering = ["-effective_date", "-created_at"]
        indexes = [
            models.Index(fields=["effective_date"], name="idx_price_date"),
            models.Index(
                fields=["listing", "effective_date"], name="idx_listing_price_date"
            ),
            models.Index(fields=["room", "effective_date"], name="idx_room_price_date"),
        ]
        constraints = [
            CheckConstraint(
                condition=Q(listing__isnull=False, room__isnull=True)
                | Q(listing__isnull=True, room__isnull=False),
                name="price_history_xor_listing_or_room",
            )
        ]

    def clean(self):
        # XOR validation for admin panel
        if (self.listing and self.room) or (not self.listing and not self.room):
            raise ValidationError(
                "The price must be linked either to the listing or to the room."
            )

        # Date validation: prevents setting prices for past dates
        if self.effective_date < timezone.now().date():
            raise ValidationError("You cannot set prices for past dates.")

    def save(self, *args, **kwargs):
        self.full_clean()

        PriceHistory.objects.filter(
            listing=self.listing, room=self.room, effective_date=self.effective_date
        ).delete()

        super().save(*args, **kwargs)
