from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.constants import (
    SEARCH_HISTORY_DEFAULT_LIMIT,
    SEARCH_HISTORY_MAX_LIMIT,
)
from apps.analytics.dto.search_history import PopularKeywordOutDTO, SearchHistoryOutDTO
from apps.analytics.paginations import AnalyticsPagination
from apps.analytics.services import SearchHistoryService


class PopularSearchKeywordsView(APIView):
    """
    GET /api/search-history/popular/?limit=10.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        limit = int(request.query_params.get("limit", SEARCH_HISTORY_DEFAULT_LIMIT))
        limit = max(1, min(limit, SEARCH_HISTORY_MAX_LIMIT))

        results = SearchHistoryService().get_popular_keywords(limit=limit)
        serializer = PopularKeywordOutDTO(results, many=True)
        return Response(serializer.data)


class MySearchHistoryView(generics.ListAPIView):
    """
    GET /api/search-history/mine/.
    DELETE /api/search-history/mine/.
    Access: authorized user.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SearchHistoryOutDTO
    pagination_class = AnalyticsPagination

    def get_queryset(self):
        return SearchHistoryService().get_my_history(self.request.user)

    def delete(self, request, *args, **kwargs):
        SearchHistoryService().clear_my_history(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
