from __future__ import annotations

from tests_e2e.actions.api.base_api_action import BaseAPIAction
from tests_e2e.actions.base import ActionResult, AnalyticsActions


class APIAnalyticsActions(BaseAPIAction, AnalyticsActions):
    def popular_search_keywords(self) -> ActionResult:
        return self._get("/search-history/popular/")

    def my_search_history(self) -> ActionResult:
        return self._get("/search-history/mine/")

    def my_view_history(self) -> ActionResult:
        return self._get("/view-history/mine/")

    def admin_dashboard_stats(self) -> ActionResult:
        return self._get("/stats/admin-dashboard/")
