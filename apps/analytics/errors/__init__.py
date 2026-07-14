class AnalyticsError(Exception):
    """Base exception apps.analytics."""

    code = "analytics_error"
    message = "Analytics module error."

    def __init__(self, message: str = None):
        self.message = message or self.message
        super().__init__(self.message)


class EmptyKeywordError(AnalyticsError):
    code = "empty_keyword"
    message = "Search keyword must not be empty after normalization."
