"""Crée les groupes de rôles métier ACGT (idempotent).

    python manage.py init_roles
"""

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from candidatures.roles import GROUPE_ADMIN, GROUPE_EVALUATEUR


class Command(BaseCommand):
    help = "Crée les groupes de rôles Administrateurs et Évaluateurs."

    def handle(self, *args, **options):
        for nom in (GROUPE_ADMIN, GROUPE_EVALUATEUR):
            groupe, cree = Group.objects.get_or_create(name=nom)
            etat = 'créé' if cree else 'déjà présent'
            self.stdout.write(self.style.SUCCESS(f'Groupe « {nom} » : {etat}'))
