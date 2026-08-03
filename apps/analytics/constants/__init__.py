# Deduplication window for a single ad view by a single user/session
VIEW_DEDUP_WINDOW_MINUTES = 15

# Default limit for GET /api/search-history/popular/ if ?limit= is not provided.
SEARCH_HISTORY_DEFAULT_LIMIT = 10
SEARCH_HISTORY_MAX_LIMIT = 100

# Pagination for "mine" endpoints (search history / viewing history).
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# drf-spectacular schema for AdminDashboard
ADMIN_DASHBOARD_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "period": {
            "type": "object",
            "properties": {
                "date_from": {"type": "string", "nullable": True},
                "date_to": {"type": "string", "nullable": True},
            },
        },
        "platform_summary": {
            "type": "object",
            "properties": {
                "total_users": {"type": "integer"},
                "listings_by_type": {
                    "type": "object",
                    "additionalProperties": {"type": "integer"},
                },
                "bookings_by_status": {
                    "type": "object",
                    "additionalProperties": {"type": "integer"},
                },
                "completed_bookings_revenue": {"type": "string"},
            },
        },
        "summary": {
            "type": "object",
            "properties": {
                "searches_count": {"type": "integer"},
                "views_count": {"type": "integer"},
            },
        },
        "gap_analysis": {
            "type": "object",
            "properties": {
                "total_zero_result_searches": {"type": "integer"},
                "recent_zero_result_searches": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "keyword": {"type": "string"},
                            "user": {"type": "string", "nullable": True},
                            "created_at": {"type": "string", "format": "date-time"},
                        },
                    },
                },
            },
        },
        "top_trending_listings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "listing_id": {"type": "string", "format": "uuid"},
                    "listing__title": {"type": "string"},
                    "views_count": {"type": "integer"},
                },
            },
        },
    },
}
