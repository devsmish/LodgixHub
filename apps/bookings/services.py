from django.utils import timezone

from apps.bookings.choices import DisputeStatus


def resolve_dispute(dispute, new_status):
    dispute.status = new_status
    dispute.resolved_at = (
        timezone.now()
        if new_status
        in (DisputeStatus.RESOLVED_REFUNDED, DisputeStatus.RESOLVED_REJECTED)
        else None
    )
    dispute.save()
