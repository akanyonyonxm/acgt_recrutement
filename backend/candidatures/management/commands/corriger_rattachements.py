"""Corrige les rattachements d'éligibilité erronés (triche par code).

Contexte : un ancien comportement rattachait automatiquement un dossier à la
ligne d'éligibilité dont le CODE correspondait. Or des candidats saisissent le
code d'autrui : le dossier se retrouvait rattaché à une personne qui n'est pas
la sienne (nom totalement différent). Le rattachement doit se faire sur le NOM
COMPLET (nom+postnom+prénom), jamais sur le code seul.

Cette commande :
  - détache (`ligne_eligibilite = None`) les dossiers dont le nom complet ne
    correspond PAS à la ligne actuellement rattachée (rattachement par code
    erroné) ;
  - tente ensuite un rattachement correct par nom complet (si une seule ligne
    de la liste porte exactement ce nom).

Opération NON destructive (on ne supprime aucune donnée ; on corrige seulement
le champ `ligne_eligibilite`). À lancer MANUELLEMENT sur le serveur — jamais
dans le pipeline de déploiement.

  python manage.py corriger_rattachements            # applique la correction
  python manage.py corriger_rattachements --simuler  # montre sans rien changer
"""

from django.core.management.base import BaseCommand

from candidatures.models import Dossier, ListeEligibilite


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
            ligne = dossier.ligne_eligibilite
            # Le rattachement est correct si le nom complet normalisé coïncide.
            if dossier.texte_recherche and dossier.texte_recherche == ligne.texte_recherche:
                conserves += 1
                continue

            # Rattachement erroné (probablement par code) → on le retire.
            ancienne = str(ligne)
            nouvelle = None
            if dossier.texte_recherche:
                candidates = list(
                    ListeEligibilite.objects
                    .filter(texte_recherche=dossier.texte_recherche)[:2]
                )
                if len(candidates) == 1:
                    nouvelle = candidates[0]

            self.stdout.write(
                f"#{dossier.pk} {dossier.nom} {dossier.postnom} {dossier.prenom} "
                f"(code {dossier.code or '-'}) : detache de « {ancienne} »"
                + (f" -> rerattache a « {nouvelle} »" if nouvelle else " -> aucun nom correspondant")
            )
            if not simuler:
                dossier.ligne_eligibilite = nouvelle
                dossier.save(update_fields=['ligne_eligibilite'])
            detaches += 1
            if nouvelle:
                rerattaches += 1

        prefixe = '[SIMULATION] ' if simuler else ''
        self.stdout.write(self.style.SUCCESS(
            f"{prefixe}Termine : {conserves} rattachements corrects conserves, "
            f"{detaches} errones detaches (dont {rerattaches} rerattaches par nom)."
        ))
