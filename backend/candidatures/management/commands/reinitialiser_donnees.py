"""Réinitialise les données opérationnelles en conservant les comptes staff.

⚠️ COMMANDE DESTRUCTIVE — À LANCER MANUELLEMENT UNIQUEMENT.
Jamais dans la CI, le déploiement ou l'entrypoint (cf. CLAUDE.md).

Supprime : dossiers (et, par cascade, pièces jointes, historique, affectations,
évaluations), fichiers physiques des pièces, liste d'éligibilité, file d'emails,
jetons email, et les comptes candidats (non-staff).

Conserve : les comptes staff (superusers, membres des groupes Administrateurs /
Évaluateurs, comptes `is_staff`), les groupes/rôles, et les référentiels de
configuration (appels, postes, types de pièce) — sauf options ci-dessous.

Exemples :
    python manage.py reinitialiser_donnees                 # aperçu (ne supprime rien)
    python manage.py reinitialiser_donnees --confirmer      # exécute
    python manage.py reinitialiser_donnees --confirmer --garder-eligibilite
    python manage.py reinitialiser_donnees --confirmer --vider-appels
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from candidatures import roles
from candidatures.models import (
    AppelCandidature,
    Dossier,
    EmailQueue,
    ListeEligibilite,
    PieceJointe,
)

User = get_user_model()


class Command(BaseCommand):
    help = (
        "Réinitialise les données opérationnelles (dossiers, pièces, candidats, "
        "éligibilité) en conservant les comptes staff. À LANCER MANUELLEMENT."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirmer', action='store_true',
            help="Exécute réellement la suppression (sinon : simple aperçu).",
        )
        parser.add_argument(
            '--garder-eligibilite', action='store_true',
            help="Conserve la liste d'éligibilité importée.",
        )
        parser.add_argument(
            '--vider-appels', action='store_true',
            help="Supprime aussi les appels à candidature (et leurs pièces exigées).",
        )

    def _comptes_candidats(self):
        """Tous les utilisateurs NON-staff (= candidats auto-inscrits)."""
        staff_ids = User.objects.filter(
            Q(is_superuser=True)
            | Q(is_staff=True)
            | Q(groups__name__in=[roles.GROUPE_ADMIN, roles.GROUPE_EVALUATEUR])
        ).values_list('id', flat=True)
        return User.objects.exclude(id__in=list(staff_ids))

    def handle(self, *args, **opts):
        confirmer = opts['confirmer']
        candidats = self._comptes_candidats()

        # Tentes auxquels on jette un œil pour l'aperçu / le compte rendu.
        plan = {
            'Dossiers (-> pieces, historique, affectations, evaluations)': Dossier.objects.count(),
            'Fichiers de pièces jointes': PieceJointe.objects.count(),
            'File d\'emails en attente': EmailQueue.objects.count(),
            'Comptes candidats (non-staff)': candidats.count(),
        }
        if not opts['garder_eligibilite']:
            plan["Lignes d'éligibilité"] = ListeEligibilite.objects.count()
        if opts['vider_appels']:
            plan['Appels à candidature'] = AppelCandidature.objects.count()

        self.stdout.write(self.style.WARNING('Éléments visés par la réinitialisation :'))
        for libelle, n in plan.items():
            self.stdout.write(f'  - {libelle} : {n}')
        gardes = User.objects.count() - candidats.count()
        self.stdout.write(self.style.SUCCESS(f'Comptes staff conservés : {gardes}'))

        if not confirmer:
            self.stdout.write(self.style.NOTICE(
                "\nAperçu uniquement — rien n'a été supprimé. "
                "Relancez avec --confirmer pour exécuter."
            ))
            return

        with transaction.atomic():
            # 1) Supprimer les fichiers physiques AVANT les lignes (la cascade SQL
            #    ne touche pas le disque).
            for piece in PieceJointe.objects.all().iterator():
                if piece.fichier:
                    piece.fichier.delete(save=False)

            # 2) Dossiers — cascade : pièces, historique, affectations, évaluations.
            Dossier.objects.all().delete()

            # 3) File d'emails + jetons (import tardif : JetonEmail vit dans comptes).
            EmailQueue.objects.all().delete()
            from comptes.models import JetonEmail
            JetonEmail.objects.all().delete()

            # 4) Éligibilité (optionnel).
            if not opts['garder_eligibilite']:
                ListeEligibilite.objects.all().delete()

            # 5) Appels à candidature (optionnel).
            if opts['vider_appels']:
                AppelCandidature.objects.all().delete()

            # 6) Comptes candidats (après les dossiers pour éviter tout conflit FK).
            self._comptes_candidats().delete()

        self.stdout.write(self.style.SUCCESS('\nOK - Reinitialisation terminee. Les comptes staff sont intacts.'))
