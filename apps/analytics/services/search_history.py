from apps.analytics.dto.search_history import SearchHistoryCreateDTO
from apps.analytics.errors import EmptyKeywordError
from apps.analytics.repositories.search_history import SearchHistoryRepository


class SearchHistoryService:
    """
    record_search is called from apps.listings.services whenever a listing search is performed.
    """

    def __init__(self, repository: SearchHistoryRepository | None = None):
        self.repository = repository or SearchHistoryRepository()

    def record_search(self, *, user, keyword: str, results_count: int | None = None):
        dto = SearchHistoryCreateDTO(
            data={"keyword": keyword, "results_count": results_count}
        )
        dto.is_valid(raise_exception=True)
        normalized_keyword = dto.validated_data["keyword"].lower()
        if not normalized_keyword:
            raise EmptyKeywordError()

        return self.repository.create(
            user=user if (user and user.is_authenticated) else None,
            keyword=normalized_keyword,
            results_count=dto.validated_data.get("results_count"),
        )

    def get_popular_keywords(self, limit: int = 10):
        return self.repository.get_popular_keywords(limit=limit)

    def get_my_history(self, user):
        return self.repository.get_for_user(user)

    def clear_my_history(self, user):
        return self.repository.delete_for_user(user)
