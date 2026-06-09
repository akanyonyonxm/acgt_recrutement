"""Importe la liste d'éligibilité depuis un fichier Excel (.xlsx).

    python manage.py import_eligibilite chemin/vers/liste.xlsx
    python manage.py import_eligibilite liste.xlsx --vider --publier

Colonnes attendues (1re ligne = en-têtes, insensible à la casse/aux accents) :
    nom | postnom | prenom | type | annee | reference
Seul « nom » est obligatoire. « type » accepte « stage » ou « candidature ».

La logique d'import est dans candidatures.services.import_eligibilite (partagée
avec l'endpoint d'upload du back-office).
"""

from django.core.management.base import BaseCommand, CommandError

from candidatures.services.import_eligibilite import (
    ImportEligibiliteErreur,
    importer_eligibles,
)


class Command(BaseCommand):
    help = "Importe la liste d'éligibilité depuis un fichier Excel."

    def add_arguments(self, parser):
        parser.add_argument('fichier', help='Chemin du fichier .xlsx')
        parser.add_argument('--vider', action='store_true',
                            help='Vide la liste existante avant import.')
        parser.add_argument('--publier', action='store_true',
                            help='Marque les lignes importées comme publiées.')

    def handle(self, *args, **options):
        try:
            r = importer_eligibles(
                options['fichier'],
                remplacer=options['vider'],
                publier=options['publier'],
            )
        except ImportEligibiliteErreur as exc:
            raise CommandError(str(exc))

        if r['supprimes']:
            self.stdout.write(self.style.WARNING(
                f"{r['supprimes']} ligne(s) existante(s) supprimée(s)."
            ))
        message = f"{r['importes']} personne(s) importée(s)"
        if r['ignorees']:
            message += f", {r['ignorees']} ligne(s) sans nom ignorée(s)"
        if r['publier']:
            message += ' et publiée(s)'
        self.stdout.write(self.style.SUCCESS(message + '.'))
