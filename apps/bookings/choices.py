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


class DisputeResolutionFavor(models.TextChoices):
    TENANT = "tenant", _("In favor of tenant")
    LANDLORD = "landlord", _("In favor of landlord")
    SPLIT = "split", _("Split between both parties")


class StandardCancellationReason(models.TextChoices):
    PERSONAL_EMERGENCY = "personal_emergency", _("Personal emergency")
    CHANGED_PLANS = "changed_plans", _("Changed plans")
    PROPERTY_UNAVAILABLE = "property_unavailable", _("Property unavailable")
    CLEANLINESS_ISSUES = "cleanliness_issues", _("Cleanliness issues")


class DisputeReason(models.TextChoices):
    CLEANLINESS = "CLEANLINESS", _("Cleanliness issues")
    AMENITIES_MISSING = "AMENITIES_MISSING", _("Amenities not available")
    DAMAGED_PROPERTY = "DAMAGED_PROPERTY", _("Property damage")
    ACCESS_ISSUES = "ACCESS_ISSUES", _("Access/Check-in issues")
    MISDESCRIPTION = "MISDESCRIPTION", _("Listing misdescription")
    UNAUTHORIZED_CHARGES = "UNAUTHORIZED_CHARGES", _("Unauthorized charges")
    EARLY_CHECK_OUT = "EARLY_CHECK_OUT", _("Early check-out request")
    CANCELLATION_DISPUTE = "CANCELLATION_DISPUTE", _("Cancellation dispute")
    NOISE_COMPLAINT = "NOISE_COMPLAINT", _("Noise complaint")
    OTHER = "OTHER", _("Other")
