from apps.bookings.models import Dispute, DisputeEvidence


class DisputeRepository:

    @staticmethod
    def get_for_booking(booking_id):
        return Dispute.objects.filter(booking_id=booking_id)

    @staticmethod
    def get_by_id(dispute_id):
        return Dispute.objects.filter(id=dispute_id).select_related("booking").first()

    @staticmethod
    def get_evidence_for_dispute(dispute_id):
        return DisputeEvidence.objects.filter(dispute_id=dispute_id)
