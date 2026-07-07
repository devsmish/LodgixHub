from django.db import models


class BlockedReason(models.TextChoices):
    SPAM = "SPAM", "Spam and advertising"
    FRAUD = "FRAUD", "Fraud"
    TOS_VIOLATION = "TOS_VIOLATION", "Violation of Terms of Use (ToS)"
    FAKE_LISTING = "FAKE_LISTING", "Fake or fraudulent advertisement"
    ABUSE = "ABUSE", "Insults, aggression, or inappropriate behavior"
    OTHER = "OTHER", "Another reason"
