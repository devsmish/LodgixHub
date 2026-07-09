from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from core.models import LogModel


class PriceHistory(LogModel):
    listing = models.ForeignKey("listings.Listing", on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    # Используем дату, установленную при создании
    effective_date = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        # Блокировка попыток записи "задним числом"
        if self.effective_date < timezone.now() - timedelta(minutes=1):
            raise ValidationError("Нельзя создавать записи о цене задним числом.")
