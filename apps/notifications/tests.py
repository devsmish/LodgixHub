from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.notifications.choices import NotificationType
from apps.notifications.models import NotificationLog

User = get_user_model()


class NotificationLogModelTestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="recipient@example.com", password="securepassword123"
        )

    def test_create_success_log(self):
        log = NotificationLog.objects.create(
            user=self.user,
            notification_type=NotificationType.BOOKING_CONFIRMED,
            success=True,
        )
        self.assertTrue(log.success)
        self.assertIsNone(log.error_message)

    def test_create_failure_log_with_error_message(self):
        log = NotificationLog.objects.create(
            user=self.user,
            notification_type=NotificationType.BOOKING_CONFIRMED,
            success=False,
            error_message="SMTP connection timed out.",
        )
        self.assertFalse(log.success)
        self.assertEqual(log.error_message, "SMTP connection timed out.")

    def test_success_with_error_message_raises(self):
        log = NotificationLog(
            user=self.user,
            notification_type=NotificationType.BOOKING_CONFIRMED,
            success=True,
            error_message="This should not be here.",
        )
        with self.assertRaises(ValidationError):
            log.full_clean()

    def test_failure_without_error_message_is_allowed(self):
        log = NotificationLog.objects.create(
            user=self.user,
            notification_type=NotificationType.BOOKING_CONFIRMED,
            success=False,
        )
        self.assertIsNone(log.error_message)

    def test_user_nullable_for_system_notifications(self):
        log = NotificationLog.objects.create(
            user=None,
            notification_type=NotificationType.PRICE_CHANGED,
            success=True,
        )
        self.assertIsNone(log.user)

    def test_user_set_null_on_user_deletion(self):
        log = NotificationLog.objects.create(
            user=self.user,
            notification_type=NotificationType.REGISTRATION,
            success=True,
        )
        User.all_objects.filter(pk=self.user.pk).delete()

        log.refresh_from_db()
        self.assertIsNone(log.user)

    def test_invalid_notification_type_raises(self):
        log = NotificationLog(
            user=self.user, notification_type="NOT_A_REAL_TYPE", success=True
        )
        with self.assertRaises(ValidationError):
            log.full_clean()

    def test_clean_is_actually_called_on_save(self):
        with self.assertRaises(ValidationError):
            NotificationLog.objects.create(
                user=self.user,
                notification_type=NotificationType.BOOKING_CONFIRMED,
                success=True,
                error_message="Should be rejected before hitting the database.",
            )

    def test_log_model_immutability(self):
        log = NotificationLog.objects.create(
            user=self.user,
            notification_type=NotificationType.NEW_REVIEW,
            success=True,
        )
        log.success = False
        with self.assertRaises(ValidationError):
            log.save()

    def test_bulk_delete_protected(self):
        NotificationLog.objects.create(
            user=self.user,
            notification_type=NotificationType.NEW_REVIEW,
            success=True,
        )
        with self.assertRaises(ValidationError):
            NotificationLog.objects.filter(user=self.user).delete()
