from django.urls import path

from apps.analytics.controller.search_history import (
    MySearchHistoryView,
    PopularSearchKeywordsView,
)
from apps.analytics.controller.stats_controller import AdminDashboardStatsView
from apps.analytics.controller.view_history import MyViewHistoryView

app_name = "analytics"

urlpatterns = [
    path(
        "search-history/popular/",
        PopularSearchKeywordsView.as_view(),
        name="search-history-popular",
    ),
    path(
        "search-history/mine/",
        MySearchHistoryView.as_view(),
        name="search-history-mine",
    ),
    path("view-history/mine/", MyViewHistoryView.as_view(), name="view-history-mine"),
    path(
        "admin/stats/",
        AdminDashboardStatsView.as_view(),
        name="admin-stats",
    ),
]
