"""
Notifications is a read-only reporting endpoint. The primary risk here isn't the business
logic—the aggregations themselves are trivial—but rather the access control configuration;
it’s easy to accidentally leave an "admin-only" endpoint set to `IsAuthenticated` (or
vice versa). That is precisely what is being verified here: one test for each role
boundary, without attempting to validate the actual content of the aggregations.
"""
class TestNotificationLogPermissions:
    def test_notification_logs_require_admin(self, tenant, landlord, moderator, admin_actor):
        """Regression: IsAdmin must check both `is_superuser` and the 'admin' group — both
        cases are covered by the `admin_actor` fixture (created via the group, not via
        `is_superuser`)."""
        assert tenant.notifications.list_logs().status == 403
        assert landlord.notifications.list_logs().status == 403
        assert moderator.notifications.list_logs().status == 403

        result = admin_actor.notifications.list_logs()
        assert result.status == 200, result.data

    def test_anonymous_cannot_see_notification_logs(self, new_actor):
        guest = new_actor()

        result = guest.notifications.list_logs()

        assert result.status in (401, 403), result.data
