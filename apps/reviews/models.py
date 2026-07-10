from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.bookings.choices import BookingStatus
from apps.bookings.constants import REVIEW_WINDOW_DAYS
from apps.bookings.models import Booking
from core.models import TimestampedModel


class Review(TimestampedModel):
    booking = models.OneToOneField(
        Booking, on_delete=models.CASCADE, related_name="review"
    )
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rating__gte=1) & models.Q(rating__lte=5),
                name="rating_range_1_5",
            )
        ]

    def clean(self):
        super().clean()
        if self.booking.status != BookingStatus.COMPLETED:
            raise ValidationError(_("Reviews are only allowed for completed bookings."))
        if timezone.now() > self.booking.check_out_at + timedelta(REVIEW_WINDOW_DAYS):
            raise ValidationError(_("Review window has expired."))
