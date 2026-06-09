"""API DRF — pilotage des statuts de dossier.

Le changement de statut ne se fait jamais par écriture directe du champ : il
passe par des actions dédiées qui valident la transition (via le modèle) et
contrôlent le rôle de l'utilisateur.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from . import roles
from .models import (
    AffectationEvaluateur,
    AppelCandidature,
    Dossier,
    Evaluation,
    ListeEligibilite,
    PieceJointe,
    Poste,
    TypePiece,
)
from .pagination import PaginationPublique
from .permissions import EstAdminOuLectureSeule
from .serializers import (
    AffectationSerializer,
    AppelCandidatureSerializer,
    ChangementStatutSerializer,
    DossierListeSerializer,
    DossierSerializer,
    EligibiliteAdminSerializer,
    EligibilitePubliqueSerializer,
    EvaluationSerializer,
    HistoriqueStatutSerializer,
    PieceJointeSerializer,
    PieceJointeUploadSerializer,
    PosteSerializer,
    RetenuPubliqueSerializer,
    TypePieceSerializer,
)
from .services.email import envoyer_email
from .utils import tokens_recherche

User = get_user_model()


class TypePieceViewSet(viewsets.ReadOnlyModelViewSet):
    """Référentiel des types de pièce (lecture seule ; édition en Django Admin)."""

    queryset = TypePiece.objects.filter(actif=True)
    serializer_class = TypePieceSerializer
    permission_classes = [AllowAny]


class PosteViewSet(viewsets.ReadOnlyModelViewSet):
    """Référentiel des postes/fonctions (lecture seule ; édition en Django Admin)."""

    queryset = Poste.objects.filter(actif=True)
    serializer_class = PosteSerializer
    permission_classes = [AllowAny]


class EligibiliteViewSet(viewsets.ReadOnlyModelViewSet):
    """Liste d'éligibilité, en lecture seule, avec recherche tolérante (?q=).

    - Public : uniquement les personnes publiées, exposées en NOM/POSTNOM/PRÉNOM.
    - Admin  : toute la liste, tous les champs (référence interne incluse), pour
      la validation des dossiers.

    L'édition se fait dans Django Admin (et via l'import Excel).
    """

    permission_classes = [AllowAny]
    pagination_class = PaginationPublique

    def get_serializer_class(self):
        if roles.est_admin(self.request.user):
            return EligibiliteAdminSerializer
        return EligibilitePubliqueSerializer

    def get_queryset(self):
        qs = ListeEligibilite.objects.all()
        if not roles.est_admin(self.request.user):
            qs = qs.filter(est_publie=True)
        # Recherche tolérante : chaque mot de la requête doit être contenu dans
        # le texte normalisé (ordre indifférent, insensible aux accents/casse).
        for token in tokens_recherche(self.request.query_params.get('q', '')):
            qs = qs.filter(texte_recherche__contains=token)
        return qs


class AppelCandidatureViewSet(viewsets.ModelViewSet):
    queryset = (
        AppelCandidature.objects
        .annotate(nb_dossiers=Count('dossiers'))
        .prefetch_related('pieces_exigees__type_piece')
    )
    serializer_class = AppelCandidatureSerializer
    # Consultable par tous (liste des appels, checklist des pièces) ; création
    # et modification réservées aux administrateurs. La config fine se fait
    # surtout en Django Admin.
    permission_classes = [EstAdminOuLectureSeule]

    @action(detail=True, methods=['post'], url_path='publier-retenus')
    def publier_retenus(self, request, pk=None):
        """Publie la liste des retenus (admin) → affichage public.

        Le candidat retenu a déjà été notifié par l'email de décision (action
        `retenir`). L'email de convocation à la publication sera ajouté plus
        tard (l'infrastructure EmailQueue / envoyer_emails_en_attente est déjà
        en place).
        """
        if not roles.est_admin(request.user):
            raise PermissionDenied("Réservé aux administrateurs.")
        appel = self.get_object()
        appel.liste_retenus_publiee = True
        appel.save(update_fields=['liste_retenus_publiee'])
        return Response({
            'detail': 'Liste des retenus publiée.',
            'retenus': appel.dossiers.filter(statut=Dossier.Statut.RETENU).count(),
        })

    @action(detail=True, methods=['post'], url_path='depublier-retenus')
    def depublier_retenus(self, request, pk=None):
        """Retire la liste des retenus de l'affichage public (admin)."""
        if not roles.est_admin(request.user):
            raise PermissionDenied("Réservé aux administrateurs.")
        appel = self.get_object()
        appel.liste_retenus_publiee = False
        appel.save(update_fields=['liste_retenus_publiee'])
        return Response({'detail': 'Liste des retenus dépubliée.'})


class RetenusViewSet(viewsets.ReadOnlyModelViewSet):
    """Liste publique des personnes retenues (lecture seule, recherche tolérante).

    N'expose que les dossiers RETENU d'un AAC dont la liste est publiée, en
    NOM/POSTNOM/PRÉNOM uniquement. Filtrer par `?appel=<id>` et rechercher
    via `?q=`.
    """

    serializer_class = RetenuPubliqueSerializer
    permission_classes = [AllowAny]
    pagination_class = PaginationPublique

    def get_queryset(self):
        qs = Dossier.objects.filter(
            statut=Dossier.Statut.RETENU,
            appel__liste_retenus_publiee=True,
        )
        appel = self.request.query_params.get('appel')
        if appel:
            qs = qs.filter(appel_id=appel)
        for token in tokens_recherche(self.request.query_params.get('q', '')):
            qs = qs.filter(texte_recherche__contains=token)
        return qs.order_by('nom', 'postnom', 'prenom')


class DossierViewSet(viewsets.ModelViewSet):
    serializer_class = DossierSerializer

    def get_serializer_class(self):
        # Liste = vue allégée (pas de N+1 sur pièces/complétude) ; détail et
        # réponses d'action = vue complète.
        if self.action == 'list':
            return DossierListeSerializer
        return DossierSerializer

    def get_queryset(self):
        """Scoping par rôle :

        - admin : tous les dossiers ;
        - évaluateur : uniquement les dossiers où il est désigné (+ les siens
          s'il a aussi déposé) ;
        - candidat : uniquement ses propres dossiers.
        """
        qs = (
            Dossier.objects
            .select_related('appel', 'deposant', 'ligne_eligibilite')
            .prefetch_related('pieces__type_piece')
        )
        user = self.request.user
        if roles.est_admin(user):
            pass
        elif roles.est_evaluateur(user):
            qs = qs.filter(
                Q(affectations__evaluateur=user) | Q(deposant=user)
            ).distinct()
        else:
            qs = qs.filter(deposant=user)

        statut = self.request.query_params.get('statut')
        appel = self.request.query_params.get('appel')
        if statut:
            qs = qs.filter(statut=statut)
        if appel:
            qs = qs.filter(appel_id=appel)
        return qs

    # --- Cycle de vie du dépôt (candidat) -------------------------------

    def perform_create(self, serializer):
        """Création d'un dossier en brouillon par un candidat à l'email vérifié."""
        user = self.request.user
        if not user.email_verifie:
            raise PermissionDenied(
                "Vous devez d'abord vérifier votre email avant de déposer un dossier."
            )
        appel = serializer.validated_data['appel']
        # Appel à candidature unique : un seul dossier par compte.
        if appel.candidature_unique and appel.dossiers.filter(deposant=user).exists():
            raise ValidationError(
                "Vous avez déjà une candidature pour cet appel : une seule est autorisée."
            )
        serializer.save(deposant=user, statut=Dossier.Statut.BROUILLON)

    def _verifier_modifiable(self, dossier):
        """Un dossier n'est éditable (CRUD, pièces) qu'en brouillon par son déposant."""
        if dossier.deposant_id != self.request.user.id and not self.request.user.is_superuser:
            raise PermissionDenied("Ce dossier ne vous appartient pas.")
        if not dossier.modifiable:
            raise ValidationError(
                "Ce dossier a déjà été soumis et n'est plus modifiable."
            )

    def update(self, request, *args, **kwargs):
        self._verifier_modifiable(self.get_object())
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        self._verifier_modifiable(self.get_object())
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Comptes de dossiers par statut (scopés par rôle), pour les KPI.

        Reprend le scoping de `get_queryset` mais sans le filtre `statut`, afin
        de fournir les totaux de chaque statut en une seule requête.
        """
        user = request.user
        qs = Dossier.objects.all()
        if roles.est_admin(user):
            pass
        elif roles.est_evaluateur(user):
            qs = qs.filter(Q(affectations__evaluateur=user) | Q(deposant=user)).distinct()
        else:
            qs = qs.filter(deposant=user)

        appel = request.query_params.get('appel')
        if appel:
            qs = qs.filter(appel_id=appel)

        par_statut = {row['statut']: row['n'] for row in qs.values('statut').annotate(n=Count('id'))}
        return Response({'total': sum(par_statut.values()), 'par_statut': par_statut})

    @action(detail=True, methods=['get', 'post'])
    def pieces(self, request, pk=None):
        """GET : liste les pièces. POST : ajoute une pièce (brouillon, déposant)."""
        dossier = self.get_object()
        if request.method == 'GET':
            return Response(
                PieceJointeSerializer(dossier.pieces.all(), many=True).data
            )

        self._verifier_modifiable(dossier)
        serializer = PieceJointeUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        type_piece = serializer.validated_data['type_piece']

        # Pièce « unique » : on refuse un second fichier du même type (sauf si
        # l'AAC autorise plusieurs fichiers pour ce type, ex. les diplômes).
        exigence = dossier.appel.pieces_exigees.filter(type_piece=type_piece).first()
        autorise_plusieurs = exigence.multiple if exigence else False
        if not autorise_plusieurs and dossier.pieces.filter(type_piece=type_piece).exists():
            raise ValidationError(
                "Cette pièce n'accepte qu'un seul fichier. Retirez l'actuel pour le remplacer."
            )

        fichier = serializer.validated_data['fichier']
        piece = serializer.save(
            dossier=dossier,
            nom_original=fichier.name[:255],
            taille=fichier.size,
        )
        return Response(
            PieceJointeSerializer(piece).data, status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['delete'],
            url_path=r'pieces/(?P<piece_id>[^/.]+)')
    def supprimer_piece(self, request, pk=None, piece_id=None):
        """Retire une pièce d'un dossier encore en brouillon."""
        dossier = self.get_object()
        self._verifier_modifiable(dossier)
        piece = get_object_or_404(PieceJointe, pk=piece_id, dossier=dossier)
        piece.fichier.delete(save=False)  # supprime le fichier physique
        piece.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'],
            url_path=r'pieces/(?P<piece_id>[^/.]+)/telecharger')
    def telecharger_piece(self, request, pk=None, piece_id=None):
        """Téléchargement protégé d'une pièce (jamais d'URL publique)."""
        dossier = self.get_object()  # déjà scopé par rôle/propriété
        piece = get_object_or_404(PieceJointe, pk=piece_id, dossier=dossier)
        try:
            fichier = piece.fichier.open('rb')
        except FileNotFoundError as exc:
            raise Http404("Fichier introuvable.") from exc
        reponse = FileResponse(fichier, as_attachment=True,
                               filename=piece.nom_original or 'piece')
        return reponse

    @action(detail=True, methods=['post'])
    def soumettre(self, request, pk=None):
        """BROUILLON → DÉPOSÉ : verrouille le dossier si toutes les pièces

        obligatoires sont présentes, puis envoie l'accusé de réception.
        """
        dossier = self.get_object()
        if dossier.deposant_id != request.user.id and not request.user.is_superuser:
            raise PermissionDenied("Ce dossier ne vous appartient pas.")
        manquantes = dossier.pieces_obligatoires_manquantes()
        if manquantes:
            raise ValidationError({
                'pieces_manquantes': [tp.libelle for tp in manquantes],
                'detail': "Des pièces obligatoires sont manquantes.",
            })
        try:
            dossier.changer_statut(
                Dossier.Statut.DEPOSE, par=request.user,
                motif='Soumission par le candidat',
            )
        except DjangoValidationError as exc:
            raise ValidationError({'detail': exc.messages})

        self._envoyer_accuse(dossier)
        return Response(self.get_serializer(dossier).data)

    def _envoyer_accuse(self, dossier):
        """Accusé de réception au candidat (best-effort : n'annule pas le dépôt)."""
        try:
            envoyer_email(
                destinataire=dossier.email,
                sujet=f'Accusé de réception — dossier #{dossier.pk}',
                template='accuse_reception.html',
                contexte={
                    'nom_candidat': f'{dossier.nom} {dossier.postnom} {dossier.prenom}'.strip(),
                    'numero_dossier': dossier.pk,
                    'appel': dossier.appel.titre,
                },
            )
        except Exception:  # noqa: BLE001 — l'échec email ne doit pas casser le dépôt
            pass

    def _transition(self, request, vers, exige_role, motif_obligatoire=False,
                    lier_eligibilite=False, verif_validateur=False, email=None):
        """Factorise les actions de transition.

        :param lier_eligibilite: si True, rattache le dossier à la ligne de la
            liste d'éligibilité passée en `eligibilite_id` (traçabilité admin).
        :param verif_validateur: si True, exige que l'utilisateur soit désigné
            ET autorisé à valider ce dossier précis.
        :param email: tuple (sujet, template) à notifier au candidat après la
            transition (best-effort, n'annule pas la transition en cas d'échec).
        """
        if not exige_role(request.user):
            raise PermissionDenied(
                "Votre rôle ne vous autorise pas cette action."
            )

        corps = ChangementStatutSerializer(data=request.data)
        corps.is_valid(raise_exception=True)
        motif = corps.validated_data['motif']
        if motif_obligatoire and not motif.strip():
            raise ValidationError({'motif': "Un motif est obligatoire."})

        dossier = self.get_object()

        if verif_validateur:
            self._verifier_validateur(dossier)

        if lier_eligibilite:
            eid = request.data.get('eligibilite_id')
            if eid:
                ligne = get_object_or_404(ListeEligibilite, pk=eid)
                dossier.ligne_eligibilite = ligne
                dossier.save(update_fields=['ligne_eligibilite'])

        try:
            dossier.changer_statut(vers, par=request.user, motif=motif)
        except DjangoValidationError as exc:
            raise ValidationError({'detail': exc.messages})

        if email:
            self._notifier(dossier, email, motif)

        return Response(self.get_serializer(dossier).data, status=status.HTTP_200_OK)

    def _notifier(self, dossier, email, motif=''):
        """Notifie le candidat d'un changement de statut (best-effort)."""
        sujet, template = email
        try:
            envoyer_email(
                destinataire=dossier.email,
                sujet=sujet,
                template=template,
                contexte={
                    'nom_candidat': f'{dossier.nom} {dossier.postnom} {dossier.prenom}'.strip(),
                    'numero_dossier': dossier.pk,
                    'appel': dossier.appel.titre,
                    'motif': motif,
                },
            )
        except Exception:  # noqa: BLE001 — l'échec email ne casse pas la transition
            pass

    # --- Actions ADMIN (dossier DÉPOSÉ) ---------------------------------

    @action(detail=True, methods=['post'])
    def approuver(self, request, pk=None):
        """DÉPOSÉ → EN_EXAMEN (admin). Accepte un `eligibilite_id` optionnel."""
        return self._transition(
            request, Dossier.Statut.EN_EXAMEN, roles.est_admin,
            lier_eligibilite=True,
            email=('Votre dossier est en cours d\'examen', 'dossier_approuve.html'),
        )

    @action(detail=True, methods=['post'])
    def rejeter(self, request, pk=None):
        """DÉPOSÉ → REJETÉ (admin, motif obligatoire)."""
        return self._transition(
            request, Dossier.Statut.REJETE, roles.est_admin,
            motif_obligatoire=True,
            email=('Décision concernant votre candidature', 'dossier_rejete.html'),
        )

    # --- Affectation des évaluateurs (admin) ----------------------------

    @action(detail=True, methods=['get', 'post'])
    def affectations(self, request, pk=None):
        """GET : liste les évaluateurs désignés. POST (admin) : en désigne un.

        Corps POST : { evaluateur_id, peut_valider (bool, défaut False) }.
        Idempotent : ré-affecter met à jour le droit de validation.
        """
        dossier = self.get_object()
        if request.method == 'GET':
            return Response(
                AffectationSerializer(dossier.affectations.all(), many=True).data
            )

        if not roles.est_admin(request.user):
            raise PermissionDenied("Seul un administrateur peut désigner un évaluateur.")
        evaluateur = get_object_or_404(User, pk=request.data.get('evaluateur_id'))
        if not roles.est_evaluateur(evaluateur):
            raise ValidationError(
                {'evaluateur_id': "Cet utilisateur n'est pas un évaluateur."}
            )
        affectation, _ = AffectationEvaluateur.objects.update_or_create(
            dossier=dossier, evaluateur=evaluateur,
            defaults={'peut_valider': bool(request.data.get('peut_valider', False))},
        )
        return Response(
            AffectationSerializer(affectation).data, status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['delete'],
            url_path=r'affectations/(?P<evaluateur_id>[^/.]+)')
    def retirer_affectation(self, request, pk=None, evaluateur_id=None):
        """Retire la désignation d'un évaluateur (admin)."""
        dossier = self.get_object()
        if not roles.est_admin(request.user):
            raise PermissionDenied("Seul un administrateur peut retirer une désignation.")
        affectation = get_object_or_404(
            AffectationEvaluateur, dossier=dossier, evaluateur_id=evaluateur_id,
        )
        affectation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # --- Évaluation (évaluateur désigné) --------------------------------

    def _verifier_designe(self, dossier):
        """L'utilisateur est-il désigné sur ce dossier (ou admin/superuser) ?"""
        user = self.request.user
        if roles.est_admin(user):
            return
        if not dossier.affectations.filter(evaluateur=user).exists():
            raise PermissionDenied("Vous n'êtes pas désigné sur ce dossier.")

    def _verifier_validateur(self, dossier):
        """L'utilisateur peut-il valider ce dossier (désigné + autorisé) ?"""
        user = self.request.user
        if user.is_superuser:
            return
        autorise = dossier.affectations.filter(
            evaluateur=user, peut_valider=True,
        ).exists()
        if not autorise:
            raise PermissionDenied(
                "Vous devez être désigné ET autorisé à valider ce dossier."
            )

    @action(detail=True, methods=['get', 'post'])
    def evaluations(self, request, pk=None):
        """GET : liste les avis. POST : enregistre/mention l'avis de l'évaluateur.

        Corps POST : { avis, recommandation }. Un évaluateur a un seul avis par
        dossier (mis à jour s'il rejoue).
        """
        dossier = self.get_object()
        if request.method == 'GET':
            self._verifier_designe(dossier)
            return Response(
                EvaluationSerializer(dossier.evaluations.all(), many=True).data
            )

        self._verifier_designe(dossier)
        evaluation = Evaluation.objects.filter(
            dossier=dossier, evaluateur=request.user,
        ).first()
        serializer = EvaluationSerializer(evaluation, data=request.data, partial=bool(evaluation))
        serializer.is_valid(raise_exception=True)
        serializer.save(dossier=dossier, evaluateur=request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # --- Décision (évaluateur désigné ET autorisé, dossier EN_EXAMEN) ----

    @action(detail=True, methods=['post'])
    def retenir(self, request, pk=None):
        """EN_EXAMEN → RETENU (évaluateur désigné et autorisé)."""
        return self._transition(
            request, Dossier.Statut.RETENU, roles.est_evaluateur,
            verif_validateur=True,
            email=('Vous êtes retenu(e) pour la suite', 'dossier_retenu.html'),
        )

    @action(detail=True, methods=['post'], url_path='non-retenir')
    def non_retenir(self, request, pk=None):
        """EN_EXAMEN → NON_RETENU (évaluateur désigné et autorisé, motif requis)."""
        return self._transition(
            request, Dossier.Statut.NON_RETENU, roles.est_evaluateur,
            motif_obligatoire=True, verif_validateur=True,
            email=('Décision concernant votre candidature', 'dossier_non_retenu.html'),
        )

    @action(detail=True, methods=['get'])
    def historique(self, request, pk=None):
        """Journal d'audit des changements de statut du dossier."""
        dossier = self.get_object()
        data = HistoriqueStatutSerializer(
            dossier.historique.all(), many=True,
        ).data
        return Response(data)
