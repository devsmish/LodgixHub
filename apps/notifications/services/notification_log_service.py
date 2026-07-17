from django.conf import settings
from django.core.mail import send_mail

from apps.notifications.models import NotificationLog


class NotificationService:
    """
    Synchronous direct email sending (without a queue for now) + auditing
    of every attempt in the NotificationLog — regardless of the outcome.
    """

    @staticmethod
    def send(*, user, notification_type, subject, message):
        if user is not None and not user.notify_by_email:
            # opt-out (User.notify_by_email) — we neither send nor
            # log this: it is not a delivery error, but a deliberate user choice.
            return None

        recipient_email = user.email if user else None
        if not recipient_email:
            return NotificationLog.objects.create(
                user=user,
                notification_type=notification_type,
                success=False,
                error_message="No recipient email available.",
            )

        success = True
        error_message = None
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email],
                fail_silently=False,
            )
        except (
            Exception
        ) as exc:  # noqa: BLE001 — Any SMTP error is logged and must not cause the request to fail.
            success = False
            error_message = str(exc)[:500]

        return NotificationLog.objects.create(
            user=user,
            notification_type=notification_type,
            success=success,
            error_message=error_message,
        )
