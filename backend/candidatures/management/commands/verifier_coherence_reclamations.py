"""Diagnostic LECTURE SEULE : écart entre « réclamations validées » et
« dossiers retenus issus d'une réclamation ».

Explique la différence parfois observée entre :
  - le compteur « Validées » de la page Réclamations (réclamations statut=VALIDEE) ;
  - le compteur « Réclamations validées » de la page Validation (dossiers RETENU
    issus d'une réclamation).

Ces deux nombres divergent quand une réclamation reste « validée » mais que le
dossier qu'elle a créé n'est plus « retenu » (rouvert / rejeté après coup), ou
n'existe plus. Cette commande NE MODIFIE RIEN — elle ne fait que lister les cas.

    python manage.py verifier_coherence_reclamations
"""

from django.core.management.base import BaseCommand
from django.db.models import Exists, OuterRef

from candidatures.models import Dossier, ReclamationEligibilite


class Command(BaseCommand):
    help = "Diagnostique l'écart réclamations validées / dossiers retenus (lecture seule)."

    def handle(self, *args, **options):
        validees = ReclamationEligibilite.objects.filter(
            statut=ReclamationEligibilite.Statut.VALIDEE,
        )
        n_validees = validees.count()

        dossiers_retenus_reclam = Dossier.objects.filter(
            statut=Dossier.Statut.RETENU,
        ).filter(
            Exists(ReclamationEligibilite.objects.filter(dossier_cree=OuterRef('pk')))
        ).count()

        self.stdout.write(f"Reclamations 'Validees'                 : {n_validees}")
        self.stdout.write(f"Dossiers RETENU issus d'une reclamation : {dossiers_retenus_reclam}")
        self.stdout.write(f"Ecart                                   : {n_validees - dossiers_retenus_reclam}")
        self.stdout.write('')

        # Reclamations validees dont le dossier cree n'est plus RETENU (ou absent).
        suspects = []
        for r in validees.select_related('dossier_cree'):
            d = r.dossier_cree
            if d is None:
                suspects.append((r, 'AUCUN DOSSIER LIE', None, None))
            elif d.statut != Dossier.Statut.RETENU:
                suspects.append((r, d.get_statut_display(), d.id, d.code))

        if not suspects:
            self.stdout.write(self.style.SUCCESS(
                "Aucune divergence : chaque reclamation validee a bien un dossier RETENU."))
            return

        self.stdout.write(self.style.WARNING(
            f"{len(suspects)} reclamation(s) validee(s) sans dossier RETENU :"))
        for r, etat, did, code in suspects:
            self.stdout.write(
                f"  - Reclamation #{r.id} {r.nom} {r.postnom} {r.prenom} "
                f"-> dossier {code or did or '-'} : {etat}"
            )
        self.stdout.write('')
        self.stdout.write(
            "Explication : ces dossiers ont ete rouverts/rejetes apres validation "
            "de la reclamation. C'est la source de l'ecart. Aucune action requise "
            "si c'est voulu ; sinon, rouvrir la reclamation ou re-valider le dossier."
        )
