from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.bookings.choices import BookingStatus, DisputeStatus
from apps.bookings.constants import (
    DISPUTE_ALLOWED_TRANSITIONS,
    DISPUTE_OPEN_WINDOW_DAYS,
)


def validate_dispute_opener(dispute):
    """Verification that a dispute is opened only by a booking participant."""
    booking = dispute.booking
    landlord = booking.get_landlord()
    allowed_opener_ids = {booking.tenant_id, getattr(landlord, "id", None)}

    if dispute.opened_by_id and dispute.opened_by_id not in allowed_opener_ids:
        raise ValidationError(
            {
                "opened_by": _(
                    "Only the tenant or the landlord of this booking can open a dispute."
                )
            }
        )


def validate_dispute_booking_status(booking):
    """A dispute can only be opened for confirmed or completed bookings."""
    if booking.status not in (BookingStatus.CONFIRMED, BookingStatus.COMPLETED):
        raise ValidationError(
            _("Disputes can only be opened for a confirmed or completed booking.")
        )


def validate_dispute_timeline(dispute):
    """Verification of the dispute opening window (after check-in and before the deadline)."""
    booking = dispute.booking
    target = booking.room if booking.room else booking.listing
    if not target:
        return

    check_in_dt = timezone.make_aware(
        datetime.combine(booking.check_in_date, target.check_in_time)
    )
    check_out_dt = timezone.make_aware(
        datetime.combine(booking.check_out_date, target.check_out_time)
    )
    now = timezone.now()

    if now < check_in_dt:
        raise ValidationError(
            _("Dispute can only be opened after check-in has started.")
        )

    deadline = check_out_dt + timedelta(days=DISPUTE_OPEN_WINDOW_DAYS)
    if now > deadline:
        raise ValidationError(
            _("Disputes can be opened only within %(days)s days after checkout.")
            % {"days": DISPUTE_OPEN_WINDOW_DAYS}
        )


def validate_duplicate_disputes(dispute, dispute_model):
    """Prohibition on creating a duplicate active dispute from the same user."""
    active_qs = dispute_model.objects.filter(
        booking=dispute.booking,
        opened_by=dispute.opened_by,
        status__in=[DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW],
    )
    if not dispute._state.adding:
        active_qs = active_qs.exclude(pk=dispute.pk)

    if active_qs.exists():
        raise ValidationError(_("You already have an active dispute on this booking."))


def validate_dispute_status_transitions(dispute, dispute_model):
    """State transition validation (Finite State Machine)."""
    if dispute._state.adding:
        return

    old_status = dispute_model.objects.get(pk=dispute.pk).status
    if old_status != dispute.status:
        allowed = DISPUTE_ALLOWED_TRANSITIONS.get(old_status, set())
        if dispute.status not in allowed:
            raise ValidationError(
                {
                    "status": _(
                        "Invalid dispute status transition: %(old)s -> %(new)s."
                    )
                    % {"old": old_status, "new": dispute.status}
                }
            )


def validate_dispute_amounts(dispute):
    """Verification of the claimed amount of damage."""
    if dispute.claim_amount < 0:
        raise ValidationError({"claim_amount": _("Claim amount cannot be negative.")})

    if dispute.claim_amount > dispute.booking.total_price:
        raise ValidationError(
            {"claim_amount": _("Claim amount cannot exceed total booking price.")}
        )


def validate_dispute_resolution(dispute):
    """Validation of mandatory fields when a moderator closes a dispute."""
    is_resolved = dispute.status in (
        DisputeStatus.RESOLVED_REFUNDED,
        DisputeStatus.RESOLVED_REJECTED,
    )
    if not is_resolved:
        return

    if not dispute.resolved_at:
        raise ValidationError(
            {"resolved_at": _("Resolution date is required for resolved disputes.")}
        )
    if not dispute.resolved_by_id:
        raise ValidationError(
            {"resolved_by": _("Resolved disputes must record who resolved them.")}
        )
    if not dispute.resolution_favor:
        raise ValidationError(
            {
                "resolution_favor": _(
                    "Resolved disputes must record who the resolution favors."
                )
            }
        )
    if (
        dispute.status == DisputeStatus.RESOLVED_REFUNDED
        and dispute.resolution_amount is None
    ):
        raise ValidationError(
            {
                "resolution_amount": _(
                    "A refunded resolution must specify the resolution amount."
                )
            }
        )


def validate_evidence_uploader(evidence):
    """Verifies that evidence is uploaded only by a party to the dispute."""
    booking = evidence.dispute.booking
    landlord = booking.get_landlord()
    allowed_uploader_ids = {booking.tenant_id, getattr(landlord, "id", None)}

    if evidence.uploaded_by_id and evidence.uploaded_by_id not in allowed_uploader_ids:
        raise ValidationError(
            {
                "uploaded_by": _(
                    "Only the tenant or the landlord of this booking can upload evidence."
                )
            }
        )
