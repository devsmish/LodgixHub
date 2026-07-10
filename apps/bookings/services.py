from django.utils import timezone


def resolve_dispute(dispute, new_status):
    dispute.status = new_status
    dispute.resolved_at = timezone.now() if new_status.startswith("RESOLVED_") else None
    dispute.save()
