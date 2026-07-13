from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import (
    MaxLengthValidator,
    MaxValueValidator,
    MinLengthValidator,
    MinValueValidator,
)
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.bookings.choices import BookingStatus
from apps.bookings.constants import REVIEW_WINDOW_DAYS
from apps.bookings.models import Booking
from apps.reviews.choices import ReviewStatus
from core.models import TimestampedModel


class Review(TimestampedModel):
    booking = models.OneToOneField(
        Booking, on_delete=models.CASCADE, related_name="review"
    )
    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.PROTECT,
        related_name="reviews",
        verbose_name=_("Listing"),
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reviews",
        verbose_name=_("Author"),
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name=_("Rating"),
    )
    comment = models.TextField(
        blank=True,
        validators=[MinLengthValidator(10), MaxLengthValidator(2000)],
        verbose_name=_("Comment"),
        help_text=_("Optional; if provided must be between 10 and 2000 characters."),
    )
    status = models.CharField(
        max_length=20,
        choices=ReviewStatus,
        default=ReviewStatus.PENDING,
        verbose_name=_("Status"),
    )
    landlord_response = models.TextField(
        blank=True, verbose_name=_("Landlord response")
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rating__gte=1) & models.Q(rating__lte=5),
                name="rating_range_1_5",
            )
        ]
        indexes = [
            models.Index(fields=["listing", "status"]),
        ]

    def clean(self):
        super().clean()

        if self.booking.status != BookingStatus.COMPLETED:
            raise ValidationError(_("Reviews are only allowed for completed bookings."))

        deadline = self.booking.check_out_date + timedelta(days=REVIEW_WINDOW_DAYS)
        if timezone.now().date() > deadline:
            raise ValidationError(_("Review window has expired."))

        if self.author_id and self.author_id != self.booking.tenant_id:
            raise ValidationError(
                {"author": _("Only the tenant of this booking can leave a review.")}
            )

        derived_listing = self.booking.listing or (
            self.booking.room.listing if self.booking.room else None
        )
        if derived_listing and self.listing_id != derived_listing.id:
            self.listing = derived_listing

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Review {self.id} for booking {self.booking_id} ({self.rating}/5)"
