from django.urls import path

from apps.pricing.controller import PriceHistoryListView, PriceSetView

app_name = "pricing"

urlpatterns = [
    path(
        "listings/<uuid:listing_id>/price/",
        PriceSetView.as_view(),
        name="listing-price-set",
    ),
    path(
        "listings/<uuid:listing_id>/price-history/",
        PriceHistoryListView.as_view(),
        name="listing-price-history",
    ),
]
