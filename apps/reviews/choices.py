from django.db import models
from django.utils.translation import gettext_lazy as _


class ReviewStatus(models.TextChoices):
    PENDING = "pending", _("Pending Moderation")
    PUBLISHED = "published", _("Published")
    HIDDEN = "hidden", _("Hidden by Moderator")
    REJECTED = "rejected", _("Rejected by Moderator")
