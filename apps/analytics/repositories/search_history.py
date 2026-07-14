from django.db.models import Count, QuerySet

from apps.analytics.models import SearchHistory


class SearchHistoryRepository:

    @staticmethod
    def create(*, user, keyword: str, results_count: int | None) -> SearchHistory:
        return SearchHistory.objects.create(
            user=user, keyword=keyword, results_count=results_count
        )

    @staticmethod
    def get_popular_keywords(limit: int) -> QuerySet:
        return (
            SearchHistory.objects.values("keyword")
            .annotate(count=Count("id"))
            .order_by("-count")[:limit]
        )

    @staticmethod
    def get_for_user(user) -> QuerySet:
        return SearchHistory.objects.filter(user=user).order_by("-created_at")

    @staticmethod
    def delete_for_user(user) -> tuple[int, dict]:
        return SearchHistory.objects.filter(user=user).delete()
