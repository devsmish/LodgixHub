from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.users.choices import BlockedReason


User = get_user_model()


class UserCoreModelTest(TestCase):

    def test_create_user_with_email(self):
        """Verifies the successful creation of a standard user with email-based authentication."""
        user = User.objects.create_user(
            email='tenant@test.com',
            password='secure_password_123'
        )
        self.assertEqual(user.email, 'tenant@test.com')
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertIsNone(user.deleted_at)

    def test_create_superuser(self):
        """Verifies the creation of a superuser with administrative privileges."""
        superuser = User.objects.create_superuser(
            email='admin@test.com',
            password='admin_password_123'
        )
        self.assertEqual(superuser.email, 'admin@test.com')
        self.assertTrue(superuser.is_active)
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)

    def test_soft_delete_user_behavior(self):
        """Verifies the soft delete functionality: the user is hidden from standard object lists."""
        user = User.objects.create_user(
            email='deleted_user@test.com',
            password='password123'
        )

        user.delete()

        self.assertIsNotNone(user.deleted_at)

        active_users = User.objects.filter(id=user.id)
        self.assertFalse(active_users.exists())

    def test_all_objects_manager_sees_deleted_users(self):
        """Verifies that the all_objects manager sees even soft-deleted users."""
        user = User.objects.create_user(
            email='archived@test.com',
            password='password123'
        )
        user.delete()

        all_users = User.all_objects.filter(id=user.id)
        self.assertTrue(all_users.exists())

    def test_restore_soft_deleted_user(self):
        """Verifies the successful restoration of the user using the .restore() method."""
        user = User.objects.create_user(
            email='comeback@test.com',
            password='password123'
        )
        user.delete()
        user.restore()

        self.assertIsNone(user.deleted_at)

        self.assertTrue(User.objects.filter(id=user.id).exists())

    def test_blocked_reason_enum_values(self):
        """Verifies that the blocking reasons from our TextChoices are preserved."""
        user = User.objects.create_user(
            email='bad_user@test.com',
            password='password123'
        )

        user.blocked_reason = BlockedReason.SPAM
        user.save()

        refreshed_user = User.objects.get(id=user.id)
        self.assertEqual(refreshed_user.blocked_reason, 'SPAM')
        self.assertEqual(refreshed_user.get_blocked_reason_display(), 'Spam and advertising')
