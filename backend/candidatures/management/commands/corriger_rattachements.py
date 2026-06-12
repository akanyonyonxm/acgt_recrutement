"""Réconcilie les rattachements d'éligibilité de tous les dossiers soumis.

Contexte : un ancien comportement rattachait un dossier à la ligne d'éligibilité
dont le CODE correspondait. Or des candidats saisissent le code d'autrui : le
dossier se retrouvait rattaché à une autre personne (triche), et des dossiers
légitimes n'étaient pas rattachés. Le rattachement doit se faire sur le NOM
(nom+postnom+prénom), jamais sur le code seul.

Cette commande parcourt **tous les dossiers soumis** (hors brouillons) et, pour
chacun, calcule la bonne correspondance par le nom — au moins 2 des 3 champs
nom/postnom/prénom coïncident, meilleure correspondance unique ; tolère une
coquille ou un champ manquant sur la liste (cf.
`Dossier.ligne_eligibilite_correspondante`). Puis :
  - **rattache** ceux qui ne le sont pas encore mais dont le nom correspond ;
  - **conserve** les rattachements déjà corrects ;
  - **détache / rerattache** les rattachements erronés (faits par code à une
    personne qui n'est pas la sienne — triche).

Opération NON destructive (on ne supprime aucune donnée ; on ne change que le
champ `ligne_eligibilite`). À lancer MANUELLEMENT sur le serveur — jamais dans
le pipeline de déploiement.

  python manage.py corriger_rattachements            # applique
  python manage.py corriger_rattachements --simuler  # montre sans rien changer
"""

from django.core.management.base import BaseCommand

from candidatures.models import Dossier


class Command(BaseCommand):
    help = "Réconcilie les rattachements d'éligibilité par le nom (tous les dossiers soumis)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--simuler', action='store_true',
            help="N'applique rien ; affiche seulement ce qui serait changé.",
        )

    def handle(self, *args, **options):
        simuler = options['simuler']
        rattaches = 0   # non rattaché → rattaché
        rerattaches = 0  # rattaché à la mauvaise personne → bonne personne
        detaches = 0    # rattaché à tort → détaché (aucun nom correspondant)
        conserves = 0   # déjà correct

        qs = (
            Dossier.objects
            .exclude(statut=Dossier.Statut.BROUILLON)
            .select_related('ligne_eligibilite')
        )
        for dossier in qs:
            ancienne = dossier.ligne_eligibilite
            correcte = dossier.ligne_eligibilite_correspondante()
            anc_id = ancienne.id if ancienne else None
            cor_id = correcte.id if correcte else None

            if anc_id == cor_id:
                if ancienne is not None:
                    conserves += 1
                continue

            qui = (f"#{dossier.pk} {dossier.nom} {dossier.postnom} {dossier.prenom} "
                   f"(code {dossier.code or '-'})")
            if ancienne is None:
                self.stdout.write(f"{qui} : rattache a « {correcte} »")
                rattaches += 1
            elif correcte is None:
                self.stdout.write(f"{qui} : detache de « {ancienne} » (aucun nom correspondant)")
                detaches += 1
            else:
                self.stdout.write(f"{qui} : « {ancienne} » -> « {correcte} »")
                rerattaches += 1

            if not simuler:
                dossier.ligne_eligibilite = correcte
                dossier.save(update_fields=['ligne_eligibilite'])

        prefixe = '[SIMULATION] ' if simuler else ''
        self.stdout.write(self.style.SUCCESS(
            f"{prefixe}Termine : {rattaches} nouveaux rattachements, "
            f"{rerattaches} rerattaches, {detaches} detaches, "
            f"{conserves} corrects conserves."
        ))
