"""Crée des postes par défaut (idempotent).

    python manage.py init_postes
"""

from django.core.management.base import BaseCommand

from candidatures.models import Poste

DEFAUTS = [
    'Architecte',
    'Ingénieur civil',
    'Ingénieur en construction',
    'Environnementaliste',
    'Géomètre topographe',
    'Conducteur des travaux',
    'Technicien de laboratoire',
    'Gestionnaire de projet',
    'Comptable',
    'Juriste',
]


class Command(BaseCommand):
    help = "Crée des postes par défaut."

    def handle(self, *args, **options):
        for ordre, libelle in enumerate(DEFAUTS):
            _, cree = Poste.objects.get_or_create(
                libelle=libelle, defaults={'ordre': ordre},
            )
            self.stdout.write(self.style.SUCCESS(
                f'{libelle} : {"créé" if cree else "déjà présent"}'
            ))
