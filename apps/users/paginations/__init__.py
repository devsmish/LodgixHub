from rest_framework.pagination import PageNumberPagination

from apps.users.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE


class UserPagination(PageNumberPagination):
    page_size = DEFAULT_PAGE_SIZE
    page_size_query_param = "page_size"
    max_page_size = MAX_PAGE_SIZE
