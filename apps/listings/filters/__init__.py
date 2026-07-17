from django.db.models import Q

from apps.listings.constants import (
    SORT_NEWEST,
    SORT_OLDEST,
    SORT_POPULAR_REVIEWS,
    SORT_POPULAR_VIEWS,
    SORT_PRICE_ASC,
    SORT_PRICE_DESC,
)

_SORT_MAPPING = {
    SORT_PRICE_ASC: "current_price",
    SORT_PRICE_DESC: "-current_price",
    SORT_NEWEST: "-created_at",
    SORT_OLDEST: "created_at",
    SORT_POPULAR_VIEWS: "-views_count",
    SORT_POPULAR_REVIEWS: "-reviews_count",
}


class ListingFilter:
    """Constructing the queryset for GET /api/v1/listings/."""

    def __init__(self, query_params):
        self.query_params = query_params

    def apply(self, queryset):
        queryset = self._filter_keyword(queryset)
        queryset = self._filter_price(queryset)
        queryset = self._filter_location(queryset)
        queryset = self._filter_rooms_count(queryset)
        queryset = self._filter_type(queryset)
        queryset = self._apply_sort(queryset)
        return queryset

    def _filter_keyword(self, queryset):
        keyword = self.query_params.get("q")
        if keyword:
            queryset = queryset.filter(
                Q(title__icontains=keyword) | Q(description__icontains=keyword)
            )
        return queryset

    def _filter_price(self, queryset):
        price_min = self.query_params.get("price_min")
        price_max = self.query_params.get("price_max")
        if price_min:
            queryset = queryset.filter(current_price__gte=price_min)
        if price_max:
            queryset = queryset.filter(current_price__lte=price_max)
        return queryset

    def _filter_location(self, queryset):
        city = self.query_params.get("city")
        district = self.query_params.get("district")
        if city:
            queryset = queryset.filter(address__city__icontains=city)
        if district:
            queryset = queryset.filter(address__district__icontains=district)
        return queryset

    def _filter_rooms_count(self, queryset):
        rooms_min = self.query_params.get("rooms_min")
        rooms_max = self.query_params.get("rooms_max")
        if rooms_min:
            queryset = queryset.filter(rooms_count__gte=rooms_min)
        if rooms_max:
            queryset = queryset.filter(rooms_count__lte=rooms_max)
        return queryset

    def _filter_type(self, queryset):
        listing_type = self.query_params.get("type")
        if listing_type:
            queryset = queryset.filter(type=listing_type)
        return queryset

    def _apply_sort(self, queryset):
        sort = self.query_params.get("sort")
        order_by = _SORT_MAPPING.get(sort)
        if order_by:
            queryset = queryset.order_by(order_by)
        return queryset
