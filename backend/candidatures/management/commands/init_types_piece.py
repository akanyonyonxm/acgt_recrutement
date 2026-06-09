"""Crée les types de pièce par défaut (idempotent).

    python manage.py init_types_piece

L'admin peut ensuite les compléter / désactiver dans Django Admin, et choisir
lesquels sont exigés par appel à candidature.
"""

from django.core.management.base import BaseCommand

from candidatures.models import TypePiece

DEFAUTS = [
    ('identite', 'Pièce d\'identité', 'Carte d\'identité, passeport ou permis.'),
    ('cv', 'Curriculum vitae', ''),
    ('lettre_motivation', 'Lettre de motivation', ''),
    ('attestation_stage', 'Attestation / lettre de stage', 'Preuve du lien avec l\'ACGT.'),
    ('demande_emploi', 'Demande d\'emploi', 'Copie de l\'ancienne demande déposée.'),
    ('diplome', 'Diplôme', ''),
    ('autre', 'Autre document', ''),
]


class Command(BaseCommand):
    help = "Crée les types de pièce par défaut."

    def handle(self, *args, **options):
        for ordre, (code, libelle, description) in enumerate(DEFAUTS):
            objet, cree = TypePiece.objects.get_or_create(
                code=code,
                defaults={'libelle': libelle, 'description': description,
                          'ordre': ordre},
            )
            etat = 'créé' if cree else 'déjà présent'
            self.stdout.write(self.style.SUCCESS(f'{libelle} : {etat}'))
