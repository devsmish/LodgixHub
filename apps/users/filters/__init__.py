class UserFilter:
    """queryset for GET /api/v1/users/ (moderator/admin)."""

    def __init__(self, query_params):
        self.query_params = query_params

    def apply(self, queryset):
        email = self.query_params.get("email")
        if email:
            queryset = queryset.filter(email__icontains=email)

        nickname = self.query_params.get("nickname")
        if nickname:
            queryset = queryset.filter(nickname__icontains=nickname)

        is_active = self.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() in ("true", "1"))

        group = self.query_params.get("group")
        if group:
            queryset = queryset.filter(groups__name__iexact=group)

        return queryset.distinct()
