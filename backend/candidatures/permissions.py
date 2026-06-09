"""Permissions DRF réutilisables, basées sur les rôles métier (roles.py)."""

from rest_framework import permissions

from . import roles


class EstAdminOuLectureSeule(permissions.BasePermission):
    """Lecture ouverte à tous ; écriture réservée aux administrateurs.

    Convient aux ressources de configuration publiquement consultables mais
    administrées par l'ACGT (appels à candidature, listes publiques).
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated
                    and roles.est_admin(request.user))
