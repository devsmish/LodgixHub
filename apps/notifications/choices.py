from django.db import models
from django.utils.translation import gettext_lazy as _


class NotificationType(models.TextChoices):
    REGISTRATION = "REGISTRATION", _("User Registration Success")
    BOOKING_CONFIRMED = "BOOKING_CONFIRMED", _("Booking Confirmed")
    BOOKING_REJECTED = "BOOKING_REJECTED", _("Booking Rejected")
    BOOKING_CANCELLED = "BOOKING_CANCELLED", _("Booking Cancelled")
    BOOKING_AUTO_CANCELLED = "BOOKING_AUTO_CANCELLED", _("Booking Auto-Cancelled")
    PRICE_CHANGED = "PRICE_CHANGED", _("Listing Price Changed")
    NEW_REVIEW = "NEW_REVIEW", _("New Guest Review Received")
    REVIEW_RESPONSE = "REVIEW_RESPONSE", _("Landlord Response to Review")
