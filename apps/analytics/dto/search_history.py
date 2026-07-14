from rest_framework import serializers

from apps.analytics.models import SearchHistory


class SearchHistoryCreateDTO(serializers.Serializer):
    """
    Input data for registering a search query. Called from within the
    listing search services (apps/listings/services) on every request
    to /api/listings/?q=...
    """

    keyword = serializers.CharField(
        max_length=255, allow_blank=False, trim_whitespace=True
    )
    results_count = serializers.IntegerField(
        min_value=0, required=False, allow_null=True
    )

    def validate_keyword(self, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise serializers.ValidationError("Keyword must not be empty after trim.")
        return normalized


class SearchHistoryOutDTO(serializers.ModelSerializer):
    class Meta:
        model = SearchHistory
        fields = ("id", "keyword", "results_count", "created_at")
        read_only_fields = fields


class PopularKeywordOutDTO(serializers.Serializer):
    """Output of the aggregation values('keyword').annotate(count=Count('id'))."""

    keyword = serializers.CharField()
    count = serializers.IntegerField()
