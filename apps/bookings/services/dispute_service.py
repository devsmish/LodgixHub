from django.utils import timezone

from apps.bookings.choices import DisputeStatus
from apps.bookings.models import Dispute, DisputeEvidence
from apps.bookings.signals import dispute_resolved


def open_dispute(*, booking, opened_by, reason_category, reason, claim_amount=0):
    dispute = Dispute(
        booking=booking,
        opened_by=opened_by,
        reason_category=reason_category,
        reason=reason,
        claim_amount=claim_amount,
    )
    dispute.save()
    return dispute


def add_evidence(*, dispute, uploaded_by, url, description=""):
    evidence = DisputeEvidence(
        dispute=dispute,
        uploaded_by=uploaded_by,
        url=url,
        description=description,
    )
    evidence.save()
    return evidence


def start_review(*, dispute, moderator):
    dispute.status = DisputeStatus.UNDER_REVIEW
    dispute.save()
    return dispute


def resolve_dispute(
    *,
    dispute,
    moderator,
    new_status,
    resolution_favor,
    resolution_amount=None,
    notes="",
):
    dispute.status = new_status
    dispute.resolved_by = moderator
    dispute.resolution_favor = resolution_favor
    dispute.resolution_amount = resolution_amount
    dispute.moderator_notes = notes
    dispute.resolved_at = timezone.now()
    dispute.save()
    dispute_resolved.send(sender=Dispute, dispute=dispute)

    return dispute
