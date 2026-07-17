from django.db import models
from django.utils.translation import gettext_lazy as _


class GenderChoices(models.TextChoices):
    MALE = "M", _("Male")
    FEMALE = "F", _("Female")
    OTHER = "X", _("Other")


class BlockedReason(models.TextChoices):
    SPAM = "SPAM", _("Spam and advertising")
    FRAUD = "FRAUD", _("Fraud")
    TOS_VIOLATION = "TOS_VIOLATION", _("Violation of Terms of Use (ToS)")
    FAKE_LISTING = "FAKE_LISTING", _("Fake or fraudulent advertisement")
    ABUSE = "ABUSE", _("Insults, aggression, or inappropriate behavior")
    OTHER = "OTHER", _("Another reason")
