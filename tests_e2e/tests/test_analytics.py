"""
Analytics/Stats — these are read-only reporting endpoints. The primary risk here lies not in
the business logic, but in the configuration of access permissions: it is easy to accidentally
leave an "admin-only" endpoint accessible to any authenticated user, or vice versa. This is
precisely what is being verified here—one test for each role boundary, without attempting to
validate the actual content of the aggregations.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.django_db(transaction=True)


class TestAnalyticsPermissions:
    def test_popular_search_keywords_is_public(self, new_actor):
        guest = new_actor()

        result = guest.analytics.popular_search_keywords()

        assert result.status == 200, result.data

    def test_my_search_history_requires_authentication(self, new_actor):
        guest = new_actor()

        result = guest.analytics.my_search_history()

        assert result.status in (401, 403), result.data

    def test_my_search_history_accessible_to_authenticated_user(self, tenant):
        result = tenant.analytics.my_search_history()

        assert result.status == 200, result.data

    def test_my_view_history_requires_authentication(self, new_actor):
        guest = new_actor()

        result = guest.analytics.my_view_history()

        assert result.status in (401, 403), result.data

    def test_admin_dashboard_stats_requires_admin(self, tenant, landlord, moderator, admin_actor):
        assert tenant.analytics.admin_dashboard_stats().status == 403
        assert landlord.analytics.admin_dashboard_stats().status == 403
        assert moderator.analytics.admin_dashboard_stats().status == 403

        result = admin_actor.analytics.admin_dashboard_stats()
        assert result.status == 200, result.data
