from django.db import models
from django.utils.translation import gettext_lazy as _


class BookingStatus(models.TextChoices):
    PENDING = "pending", _("Pending Confirmation")
    CONFIRMED = "confirmed", _("Confirmed")
    REJECTED = "rejected", _("Rejected by Landlord")
    CANCELLED_BY_TENANT = "cancelled_by_tenant", _("Cancelled by Tenant")
    CANCELLED_BY_LANDLORD = "cancelled_by_landlord", _("Cancelled by Landlord")
    AUTO_CANCELLED = "auto_cancelled", _("System Auto-Cancelled")
    COMPLETED = "completed", _("Completed")


class DisputeStatus(models.TextChoices):
    OPEN = "open", _("Dispute Opened")
    UNDER_REVIEW = "under_review", _("Under Review by Moderator")
    RESOLVED_REFUNDED = "resolved_refunded", _("Resolved with Full/Partial Refund")
    RESOLVED_REJECTED = "resolved_rejected", _("Resolved - Claim Rejected")


class CancellationReason(models.TextChoices):
    PERSONAL_EMERGENCY = "personal_emergency", _("Personal emergency")
    CHANGED_PLANS = "changed_plans", _("Changed plans")
    PROPERTY_UNAVAILABLE = "property_unavailable", _("Property unavailable")
    CLEANLINESS_ISSUES = "cleanliness_issues", _("Cleanliness issues")

    @classmethod
    def get_description(cls, code):
        return dict(cls.choices).get(code)
