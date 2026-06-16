"""Génère un jeu de données de TEST (doublons + croisements) — usage LOCAL.

But : remplir la base de dev avec des cas variés pour tester le back-office :
  - doublons de dossiers (même nom complet, même appel) ;
  - doublons de réclamations (même nom, même appel) ;
  - croisements réclamation ↔ dossier déposé (même personne) ;
  - correspondances d'éligibilité variées (rattaché / à rattacher / partielle / aucune) ;
  - un dossier EN_EXAMEN (regroupé dans « à valider »).

⚠️ Commande MANUELLE uniquement (jamais en CI / entrypoint) : elle CRÉE des
données. `--purge` supprime proprement le jeu de test (et rien d'autre).

    python manage.py seed_donnees_test          # crée (purge d'abord si déjà là)
    python manage.py seed_donnees_test --purge   # supprime seulement
"""

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from candidatures.models import (
    AppelCandidature, DocumentReclamation, Dossier, ListeEligibilite,
    PieceJointe, ReclamationEligibilite, TypePiece,
)

# PDF minimal valide (page blanche) — suffisant pour tester aperçu/téléchargement.
PDF_MINIMAL = (
    b'%PDF-1.1\n'
    b'1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n'
    b'2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n'
    b'3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 300]>>endobj\n'
    b'trailer<</Root 1 0 R>>\n%%EOF\n'
)

TITRE_APPEL = 'TEST — Doublons & croisements (données de test)'
REF_PREFIX = 'TESTSEED-'
EMAIL_DOMAINE = 'test.local'


class Command(BaseCommand):
    help = "Génère (ou purge) un jeu de données de test : doublons et croisements."

    def add_arguments(self, parser):
        parser.add_argument('--purge', action='store_true',
                            help='Supprime le jeu de test au lieu de le créer.')

    def handle(self, *args, **options):
        if options['purge']:
            self._purger()
            self.stdout.write(self.style.SUCCESS('Jeu de test supprimé.'))
            return
        with transaction.atomic():
            self._purger()        # repart d'un état propre (idempotent)
            self._creer()
        self.stdout.write(self.style.SUCCESS('Jeu de test créé.'))

    # ------------------------------------------------------------------
    def _purger(self):
        appel = AppelCandidature.objects.filter(titre=TITRE_APPEL).first()
        if appel:
            # Supprime d'abord les fichiers physiques de test (justificatifs + pièces).
            for d in DocumentReclamation.objects.filter(reclamation__appel=appel):
                d.fichier.delete(save=False)
            for p in PieceJointe.objects.filter(dossier__appel=appel):
                p.fichier.delete(save=False)
            # Réclamations d'abord (FK PROTECT vers l'appel), puis dossiers.
            ReclamationEligibilite.objects.filter(appel=appel).delete()
            Dossier.objects.filter(appel=appel).delete()
            appel.delete()
        ListeEligibilite.objects.filter(reference__startswith=REF_PREFIX).delete()

    # ------------------------------------------------------------------
    def _creer(self):
        appel = AppelCandidature.objects.create(
            titre=TITRE_APPEL, statut=AppelCandidature.Statut.PUBLIE,
            description='Appel factice pour tester le traitement (doublons, croisements).',
        )

        def elig(nom, postnom, prenom, code, ref):
            return ListeEligibilite.objects.create(
                nom=nom, postnom=postnom, prenom=prenom, code=code,
                reference=f'{REF_PREFIX}{ref}', est_publie=True,
            )

        def email(prenom, nom):
            return f'{prenom}.{nom}@{EMAIL_DOMAINE}'.lower().replace(' ', '')

        # Types de pièces pour attacher des fichiers (réutilise l'existant).
        types_piece = list(TypePiece.objects.all()[:3])
        if not types_piece:
            types_piece = [
                TypePiece.objects.get_or_create(code=c, defaults={'libelle': l})[0]
                for c, l in (('cv', 'CV'), ('identite', "Pièce d'identité"),
                             ('diplome', 'Diplôme'))
            ]

        def dossier(nom, postnom, prenom, statut=Dossier.Statut.DEPOSE,
                    code='', ligne=None):
            d = Dossier.objects.create(
                appel=appel, nom=nom, postnom=postnom, prenom=prenom,
                email=email(prenom, nom), statut=statut, code=code,
                ligne_eligibilite=ligne,
            )
            # Pièces jointes factices sur les dossiers déposés (pour tester
            # l'aperçu des pièces, y compris depuis une réclamation croisée).
            if statut == Dossier.Statut.DEPOSE:
                base = f'{nom}_{prenom}'.replace(' ', '')
                for tp in types_piece:
                    nf = f'{base}_{tp.code or tp.id}.pdf'
                    PieceJointe.objects.create(
                        dossier=d, type_piece=tp,
                        fichier=ContentFile(PDF_MINIMAL, name=nf),
                        nom_original=nf, taille=len(PDF_MINIMAL),
                    )
            return d

        def reclam(nom, postnom, prenom):
            r = ReclamationEligibilite.objects.create(
                appel=appel, nom=nom, postnom=postnom, prenom=prenom,
                email=email(prenom, nom), telephone='+243800000000',
                message='Réclamation de test (déposée hors ligne, sans réponse).',
            )
            # Justificatifs factices (PDF page blanche) pour tester aperçu/liste.
            base = f'{nom}_{prenom}'.replace(' ', '')
            for type_doc, suffixe in (
                (DocumentReclamation.Type.ACCUSE, 'accuse'),
                (DocumentReclamation.Type.CV, 'cv'),
                (DocumentReclamation.Type.IDENTITE, 'identite'),
                (DocumentReclamation.Type.DIPLOME, 'diplome'),
            ):
                nom_fichier = f'{base}_{suffixe}.pdf'
                DocumentReclamation.objects.create(
                    reclamation=r, type=type_doc,
                    fichier=ContentFile(PDF_MINIMAL, name=nom_fichier),
                    nom_original=nom_fichier, taille=len(PDF_MINIMAL),
                )
            return r

        # --- Liste d'éligibilité (publiée) ---
        e_mukendi = elig('MUKENDI', 'Jean', 'Pierre', 'TST001', 'E1')
        e_kabila = elig('KABILA', 'Joseph', 'Marie', 'TST002', 'E2')
        elig('NGOY', '', '', 'TST003', 'E3')          # nom seul → correspondance partielle
        elig('LUMUMBA', 'Patrice', 'Emery', 'TST004', 'E4')

        # --- Dossiers ---
        # Doublon : 2 dossiers même nom complet (MUKENDI Jean Pierre), non rattachés
        # → tous deux « à rattacher » + signalés en doublon l'un de l'autre.
        dossier('MUKENDI', 'Jean', 'Pierre', code='TST001')
        dossier('MUKENDI', 'Jean', 'Pierre', code='TST001')
        # Rattaché à une ligne d'éligibilité.
        dossier('KABILA', 'Joseph', 'Marie', code='TST002', ligne=e_kabila)
        # Correspondance partielle (le nom NGOY existe seul dans la liste).
        dossier('NGOY', 'Patrick', 'Kevin')
        # Aucune correspondance.
        dossier('ZALANGA', 'Innocent', 'Christophe')
        # Croisement : ces personnes ont AUSSI une réclamation (voir plus bas).
        dossier('BISIMWA', 'Serge', 'Olivier')
        # Un dossier EN_EXAMEN (doit apparaître dans « À valider »).
        dossier('TSHALA', 'Marie', 'Claire', statut=Dossier.Statut.EN_EXAMEN)
        # Un peu de variété pour les KPI.
        dossier('MOBUTU', 'Sese', 'Seko', statut=Dossier.Statut.RETENU)
        dossier('ILUNGA', 'Albert', 'Désiré', statut=Dossier.Statut.REJETE)

        # --- Réclamations ---
        # Croisements (même nom qu'un dossier DÉPOSÉ → badge « a déjà un dossier »).
        reclam('BISIMWA', 'Serge', 'Olivier')      # ↔ dossier déposé BISIMWA
        reclam('KABILA', 'Joseph', 'Marie')        # ↔ dossier déposé KABILA (rattaché)
        # Doublon de réclamations (même nom, même appel, non rejetées).
        reclam('LUMUMBA', 'Patrice', 'Emery')
        reclam('LUMUMBA', 'Patrice', 'Emery')
        # Réclamation isolée (ni doublon, ni dossier).
        reclam('KASA-VUBU', 'Joseph', 'Antoine')

        # Récapitulatif
        nd = Dossier.objects.filter(appel=appel).count()
        nr = ReclamationEligibilite.objects.filter(appel=appel).count()
        self.stdout.write(
            f"Appel '{TITRE_APPEL}' : {nd} dossier(s), {nr} reclamation(s).\n"
            "  - doublons dossiers : MUKENDI Jean Pierre (x2)\n"
            "  - doublons reclamations : LUMUMBA Patrice Emery (x2)\n"
            "  - croisements reclamation/dossier : BISIMWA, KABILA\n"
            "  - eligibilite : rattache (KABILA), a rattacher (MUKENDI), "
            "partielle (NGOY), aucune (ZALANGA)\n"
            "  - 1 dossier EN_EXAMEN (TSHALA) -> visible dans 'A valider'"
        )
