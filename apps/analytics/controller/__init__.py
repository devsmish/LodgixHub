from apps.analytics.controller.search_history import (
    MySearchHistoryView,
    PopularSearchKeywordsView,
)
from apps.analytics.controller.stats_controller import AdminDashboardStatsView
from apps.analytics.controller.view_history import MyViewHistoryView

__all__ = [
    "PopularSearchKeywordsView",
    "MySearchHistoryView",
    "MyViewHistoryView",
    "AdminDashboardStatsView",
]
