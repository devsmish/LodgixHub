from django.urls import path

from apps.analytics.controller import (
    MySearchHistoryView,
    MyViewHistoryView,
    PopularSearchKeywordsView,
)
from apps.analytics.stats_controller import AdminDashboardStatsView

app_name = "analytics"

urlpatterns = [
    path("search-history/popular/", PopularSearchKeywordsView.as_view(), name="search-history-popular"),
    path("search-history/mine/", MySearchHistoryView.as_view(), name="search-history-mine"),
    path("view-history/mine/", MyViewHistoryView.as_view(), name="view-history-mine"),

    path("stats/admin-dashboard/", AdminDashboardStatsView.as_view(), name="admin-dashboard-stats"),
]
