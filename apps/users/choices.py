from django.db import models
from django.utils.translation import gettext_lazy as _


class GenderChoices(models.TextChoices):
    MALE = "M", _("Male")
    FEMALE = "F", _("Female")
    OTHER = "X", _("Other")


class BlockedReason(models.TextChoices):
    SPAM = "SPAM", "Spam and advertising"
    FRAUD = "FRAUD", "Fraud"
    TOS_VIOLATION = "TOS_VIOLATION", "Violation of Terms of Use (ToS)"
    FAKE_LISTING = "FAKE_LISTING", "Fake or fraudulent advertisement"
    ABUSE = "ABUSE", "Insults, aggression, or inappropriate behavior"
    OTHER = "OTHER", "Another reason"
