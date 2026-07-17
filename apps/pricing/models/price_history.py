from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import CheckConstraint, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.models import LogManager, LogModel, LogQuerySet


class PriceHistoryQuerySet(LogQuerySet):
    def effective_on(self, target_date, *, listing=None, room=None):
        qs = self.filter(valid_from__lte=target_date)
        if listing is not None:
            qs = qs.filter(listing=listing)
        if room is not None:
            qs = qs.filter(room=room)
        return qs.order_by("-valid_from", "-created_at")


class PriceHistoryManager(LogManager):
    def get_queryset(self) -> PriceHistoryQuerySet:
        return PriceHistoryQuerySet(self.model, using=self._db)

    def effective_on(self, target_date, *, listing=None, room=None):
        return self.get_queryset().effective_on(target_date, listing=listing, room=room)


class PriceHistory(LogModel):

    listing = models.ForeignKey(
        "listings.Listing", on_delete=models.CASCADE, null=True, blank=True
    )
    room = models.ForeignKey(
        "listings.Room", on_delete=models.CASCADE, null=True, blank=True
    )

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        verbose_name=_("Price"),
    )
    currency = models.CharField(max_length=3, default="EUR")
    valid_from = models.DateField(default=timezone.now, verbose_name=_("Valid from"))

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="price_changes",
        verbose_name=_("Changed by"),
    )

    objects = PriceHistoryManager()

    class Meta:
        ordering = ["-valid_from", "-created_at"]
        indexes = [
            models.Index(fields=["valid_from"], name="idx_price_date"),
            models.Index(
                fields=["listing", "valid_from"], name="idx_listing_price_date"
            ),
            models.Index(fields=["room", "valid_from"], name="idx_room_price_date"),
        ]
        constraints = [
            CheckConstraint(
                condition=Q(listing__isnull=False, room__isnull=True)
                | Q(listing__isnull=True, room__isnull=False),
                name="price_history_xor_listing_or_room",
            )
        ]

    def clean(self):
        if (self.listing and self.room) or (not self.listing and not self.room):
            raise ValidationError(
                _("The price must be linked either to the listing or to the room.")
            )

        today = timezone.now().date()

        if self.valid_from < today:
            raise ValidationError(
                {"valid_from": _("You cannot set prices for past dates.")}
            )

        is_first_price = not PriceHistory.objects.filter(
            listing=self.listing, room=self.room
        ).exists()
        if self.valid_from == today and not is_first_price:
            raise ValidationError(
                {
                    "valid_from": _(
                        "Cannot set a price effective today, except for the very "
                        "first price when the listing is created."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        target = self.listing_id or self.room_id
        return f"{target}: {self.price} {self.currency} from {self.valid_from}"
