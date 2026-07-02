from rest_framework.pagination import PageNumberPagination


class PaginationPublique(PageNumberPagination):
    """Pagination des listes publiques : 10 par page, navigation à la demande."""

    page_size = 10
    page_size_query_param = 'page_size'
    # Permet d'afficher une liste complète (ex. tous les admis d'un domaine) en
    # une seule page côté public, sans pagination.
    max_page_size = 2000


class PaginationStandard(PageNumberPagination):
    """Pagination des listes back-office : 25 par page, taille ajustable."""

    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 200
