"""Corrige les rattachements d'éligibilité erronés (triche par code).

Contexte : un ancien comportement rattachait automatiquement un dossier à la
ligne d'éligibilité dont le CODE correspondait. Or des candidats saisissent le
code d'autrui : le dossier se retrouvait rattaché à une personne qui n'est pas
la sienne (nom totalement différent). Le rattachement doit se faire sur le NOM
COMPLET (nom+postnom+prénom), jamais sur le code seul.

Cette commande, pour chaque dossier rattaché, recalcule la bonne correspondance
par le nom (au moins 2 des 3 champs nom/postnom/prénom — tolère une coquille ou
un champ manquant ; cf. `Dossier.ligne_eligibilite_correspondante`) et :
  - conserve le rattachement s'il est correct ;
  - le remplace (détache, ou rerattache à la bonne personne) sinon — ce qui
    retire les rattachements faits par code à une personne qui n'est pas la
    sienne (triche).

Opération NON destructive (on ne supprime aucune donnée ; on corrige seulement
le champ `ligne_eligibilite`). À lancer MANUELLEMENT sur le serveur — jamais
dans le pipeline de déploiement.

  python manage.py corriger_rattachements            # applique la correction
  python manage.py corriger_rattachements --simuler  # montre sans rien changer
"""

from django.core.management.base import BaseCommand

from candidatures.models import Dossier


class Command(BaseCommand):
    help = "Corrige les rattachements d'éligibilité faits par code (au lieu du nom)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--simuler', action='store_true',
            help="N'applique rien ; affiche seulement ce qui serait corrigé.",
        )

    def handle(self, *args, **options):
        simuler = options['simuler']
        detaches = 0
        rerattaches = 0
        conserves = 0

        qs = (
            Dossier.objects
            .filter(ligne_eligibilite__isnull=False)
            .select_related('ligne_eligibilite')
        )
        for dossier in qs:
            ancienne = dossier.ligne_eligibilite
            # La bonne correspondance par le nom (≥2 champs sur 3), ou None.
            correcte = dossier.ligne_eligibilite_correspondante()

            # Rattachement déjà correct → on n'y touche pas.
            if correcte is not None and correcte.id == ancienne.id:
                conserves += 1
                continue

            self.stdout.write(
                f"#{dossier.pk} {dossier.nom} {dossier.postnom} {dossier.prenom} "
                f"(code {dossier.code or '-'}) : detache de « {ancienne} »"
                + (f" -> rerattache a « {correcte} »" if correcte else " -> aucun nom correspondant")
            )
            if not simuler:
                dossier.ligne_eligibilite = correcte
                dossier.save(update_fields=['ligne_eligibilite'])
            detaches += 1
            if correcte:
                rerattaches += 1

        prefixe = '[SIMULATION] ' if simuler else ''
        self.stdout.write(self.style.SUCCESS(
            f"{prefixe}Termine : {conserves} rattachements corrects conserves, "
            f"{detaches} errones detaches (dont {rerattaches} rerattaches par nom)."
        ))
