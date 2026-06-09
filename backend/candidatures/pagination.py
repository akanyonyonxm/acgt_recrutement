from rest_framework.pagination import PageNumberPagination


class PaginationPublique(PageNumberPagination):
    """Pagination des listes publiques : 10 par page, navigation à la demande."""

    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100
