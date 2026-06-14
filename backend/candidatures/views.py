"""API DRF — pilotage des statuts de dossier.

Le changement de statut ne se fait jamais par écriture directe du champ : il
passe par des actions dédiées qui valident la transition (via le modèle) et
contrôlent le rôle de l'utilisateur.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Q
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from . import roles
from .models import (
    EXTENSIONS_AUTORISEES,
    TAILLE_MAX_PIECE,
    AffectationEvaluateur,
    AppelCandidature,
    DocumentReclamation,
    Dossier,
    EmailQueue,
    Evaluation,
    ListeEligibilite,
    PieceJointe,
    Poste,
    ReclamationEligibilite,
    TypePiece,
)
from .pagination import PaginationPublique, PaginationStandard
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
    ModificationIdentiteSerializer,
    ModificationNomEligibiliteSerializer,
    PieceJointeSerializer,
    PieceJointeUploadSerializer,
    PosteSerializer,
    ReclamationAdminSerializer,
    ReclamationCreationSerializer,
    RetenuPubliqueSerializer,
    TypePieceSerializer,
)
from .services.email import envoyer_email
from .services.import_eligibilite import ImportEligibiliteErreur, importer_eligibles
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

    def _staff(self):
        return roles.acces_backoffice(self.request.user)

    def get_serializer_class(self):
        if self._staff():
            return EligibiliteAdminSerializer
        return EligibilitePubliqueSerializer

    def get_queryset(self):
        qs = ListeEligibilite.objects.all()
        if not self._staff():
            qs = qs.filter(est_publie=True)
        # Recherche tolérante : chaque mot de la requête doit être contenu dans
        # le texte normalisé (ordre indifférent, insensible aux accents/casse).
        for token in tokens_recherche(self.request.query_params.get('q', '')):
            qs = qs.filter(texte_recherche__contains=token)
        return qs

    @action(detail=True, methods=['patch'], url_path='nom')
    def modifier_nom(self, request, pk=None):
        """Corrige le NOM (nom/postnom/prénom) d'une personne de la liste.

        Réservé aux administrateurs et correcteurs. Le **code n'est pas
        modifiable** ici (identifiant stable). `texte_recherche` est recalculé
        (les correspondances avec les dossiers restent cohérentes).
        """
        if not (roles.est_admin(request.user) or roles.est_correcteur(request.user)):
            raise PermissionDenied(
                "Seuls les administrateurs et correcteurs peuvent corriger un nom."
            )
        ligne = self.get_object()
        serializer = ModificationNomEligibiliteSerializer(ligne, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(EligibiliteAdminSerializer(ligne).data)

    @action(detail=False, methods=['get'], url_path='verifier-code')
    def verifier_code(self, request):
        """Vérifie qu'un code figure sur la liste publiée (aide à la saisie).

        Renvoie le nom tel qu'écrit sur la liste, à titre de repère visuel
        uniquement : le code seul fait foi, aucune comparaison de noms n'est
        faite et rien n'est bloquant. N'expose que des données déjà publiques
        (la liste des éligibles affiche code + noms).
        """
        code = (request.query_params.get('code') or '').strip()
        if not code:
            return Response({'trouve': False, 'multiple': False, 'ligne': None})
        lignes = list(
            ListeEligibilite.objects.filter(est_publie=True, code__iexact=code)[:2]
        )
        if not lignes:
            return Response({'trouve': False, 'multiple': False, 'ligne': None})
        if len(lignes) > 1:
            # Code ambigu (présent sur plusieurs lignes) : reconnu, mais sans
            # nom affichable ni rattachement automatique possible.
            return Response({'trouve': True, 'multiple': True, 'ligne': None})
        ligne = lignes[0]
        return Response({
            'trouve': True, 'multiple': False,
            'ligne': {
                'id': ligne.id, 'code': ligne.code, 'nom': ligne.nom,
                'postnom': ligne.postnom, 'prenom': ligne.prenom,
            },
        })

    @action(detail=False, methods=['post'], url_path='importer',
            parser_classes=[MultiPartParser, FormParser])
    def importer(self, request):
        """Importe un classeur Excel d'éligibles (admin).

        Champs multipart : `fichier` (.xlsx), `remplacer` (bool : vider d'abord),
        `publier` (bool : publier les lignes importées). Renvoie le récapitulatif.
        """
        if not roles.est_admin(request.user):
            raise PermissionDenied("Réservé aux administrateurs.")

        fichier = request.FILES.get('fichier')
        if not fichier:
            raise ValidationError({'fichier': "Aucun fichier fourni."})
        if not fichier.name.lower().endswith('.xlsx'):
            raise ValidationError({'fichier': "Format attendu : .xlsx"})

        def vrai(v):
            return str(v).lower() in ('1', 'true', 'on', 'oui')

        try:
            resultat = importer_eligibles(
                fichier,
                remplacer=vrai(request.data.get('remplacer')),
                publier=vrai(request.data.get('publier')),
            )
        except ImportEligibiliteErreur as exc:
            raise ValidationError({'detail': str(exc)})
        return Response(resultat)

    @action(detail=False, methods=['get'], url_path='modele')
    def modele(self, request):
        """Télécharge un modèle Excel vierge (en-têtes attendus) pour l'import."""
        if not roles.est_admin(request.user):
            raise PermissionDenied("Réservé aux administrateurs.")

        from openpyxl import Workbook
        from openpyxl.styles import Font
        from openpyxl.utils import get_column_letter

        wb = Workbook()
        ws = wb.active
        ws.title = 'Éligibles'
        entetes = ['code', 'nom', 'postnom', 'prenom', 'type', 'annee', 'reference']
        ws.append(entetes)
        for cell in ws[1]:
            cell.font = Font(bold=True)
        # Ligne-guide SANS nom : ignorée à l'import (« nom » obligatoire), mais
        # montre le format attendu sans risquer d'importer une fausse personne.
        # type et reference laissés vides (facultatifs).
        ws.append(['ACGT-001', '', 'Mukendi', 'Jean', '', 2021, ''])
        for i, largeur in enumerate([14, 18, 18, 18, 16, 8, 16], start=1):
            ws.column_dimensions[get_column_letter(i)].width = largeur

        reponse = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        reponse['Content-Disposition'] = 'attachment; filename="modele_eligibles.xlsx"'
        wb.save(reponse)
        return reponse


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

        C'est le SEUL moment où des emails partent : aucun email n'est envoyé
        pendant le traitement. On met en file (`EmailQueue`) l'email de
        convocation pour chaque retenu pas encore mis en file (idempotent :
        republier ne recrée pas de doublon). Les envois sont ensuite lissés par
        `python manage.py envoyer_emails_en_attente --limite N` (cron), pour
        respecter la limite quotidienne de Resend.
        """
        if not roles.est_admin(request.user):
            raise PermissionDenied("Réservé aux administrateurs.")
        appel = self.get_object()
        appel.liste_retenus_publiee = True
        appel.save(update_fields=['liste_retenus_publiee'])

        retenus = appel.dossiers.filter(statut=Dossier.Statut.RETENU)
        deja = set(
            EmailQueue.objects.filter(dossier__appel=appel)
            .values_list('dossier_id', flat=True)
        )
        def _code(d):
            return d.code or f'#{d.pk}'

        a_creer = [
            EmailQueue(
                dossier=d, destinataire=d.email,
                sujet=f'Résultat de votre candidature — dossier {_code(d)}',
                template='convocation_retenu.html',
                contexte={
                    'nom_candidat': f'{d.nom} {d.postnom} {d.prenom}'.strip(),
                    'code_dossier': _code(d),
                    'appel': appel.titre,
                },
            )
            for d in retenus if d.id not in deja and d.email
        ]
        EmailQueue.objects.bulk_create(a_creer)
        return Response({
            'detail': 'Liste des retenus publiée.',
            'retenus': retenus.count(),
            'emails_en_file': len(a_creer),
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
    pagination_class = PaginationStandard

    # Champs autorisés au tri (allowlist : évite l'injection de champs arbitraires).
    TRI_AUTORISE = {'id', 'code', 'nom', 'statut', 'cree_le', 'poste__libelle', 'appel__titre'}

    def get_serializer_class(self):
        # Liste = vue allégée (pas de N+1 sur pièces/complétude) ; détail et
        # réponses d'action = vue complète.
        if self.action == 'list':
            return DossierListeSerializer
        return DossierSerializer

    @staticmethod
    def _doublon_exists():
        """Sous-requête : ce dossier a-t-il un jumeau SOUMIS (hors brouillon et
        rejeté) du même appel et même nom complet ? Réutilisée par l'annotation
        de liste et par la navigation « doublon suivant »."""
        return Exists(
            Dossier.objects
            .filter(appel_id=OuterRef('appel_id'))
            .exclude(statut__in=[Dossier.Statut.BROUILLON, Dossier.Statut.REJETE])
            .exclude(texte_recherche='')
            .filter(texte_recherche=OuterRef('texte_recherche'))
            .exclude(pk=OuterRef('pk'))
        )

    def get_queryset(self):
        """Scoping par rôle :

        - admin : tous les dossiers ;
        - évaluateur : uniquement les dossiers où il est désigné (+ les siens
          s'il a aussi déposé) ;
        - candidat : uniquement ses propres dossiers.
        """
        # Correspondance avec la liste d'éligibilité (badge indicatif, jamais
        # bloquant) : on indique précisément quels champs coïncident (code, nom,
        # postnom, prénom). Comparaison insensible à la casse (`iexact`) ;
        # l'insensibilité aux accents viendra avec `unaccent` en prod (cf.
        # CLAUDE.md). Un champ ne compte que s'il est renseigné des deux côtés
        # (jamais de faux match sur un champ vide). Calcul en SQL (Exists) pour
        # éviter tout N+1.
        qs = (
            Dossier.objects
            .select_related('appel', 'deposant', 'ligne_eligibilite')
            .prefetch_related('pieces__type_piece')
            .annotate(
                corresp_code=Exists(
                    ListeEligibilite.objects.exclude(code='')
                    .filter(code__iexact=OuterRef('code'))
                ),
                # Nom complet (nom+postnom+prénom) trouvé sur une même ligne →
                # « à rattacher » : c'est très probablement la personne.
                corresp_nom_complet=Exists(
                    ListeEligibilite.objects.exclude(texte_recherche='')
                    .filter(texte_recherche=OuterRef('texte_recherche'))
                ),
                corresp_f_nom=Exists(
                    ListeEligibilite.objects.exclude(nom='')
                    .filter(nom__iexact=OuterRef('nom'))
                ),
                corresp_f_postnom=Exists(
                    ListeEligibilite.objects.exclude(postnom='')
                    .filter(postnom__iexact=OuterRef('postnom'))
                ),
                corresp_f_prenom=Exists(
                    ListeEligibilite.objects.exclude(prenom='')
                    .filter(prenom__iexact=OuterRef('prenom'))
                ),
                # Doublon probable : un AUTRE dossier SOUMIS (hors brouillon) du
                # même appel a le même NOM COMPLET (nom+postnom+prénom normalisé).
                # On n'utilise PAS l'email : un proche peut déposer plusieurs
                # dossiers (personnes différentes) depuis la même adresse. On
                # ignore les brouillons (non traités). Indicatif : l'admin tranche.
                a_doublon=self._doublon_exists(),
            )
        )
        user = self.request.user
        if roles.acces_backoffice(user):
            pass  # tout rôle back-office (admin, validateur, correcteur, lecteur) voit tout
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

        # Filtre par correspondance avec la liste d'éligibilité (buckets alignés
        # sur les badges de la colonne « Éligibilité »).
        corr = self.request.query_params.get('correspondance')
        if corr == 'rattache':
            qs = qs.filter(ligne_eligibilite__isnull=False)
        elif corr == 'a_rattacher':
            qs = qs.filter(ligne_eligibilite__isnull=True, corresp_nom_complet=True)
        elif corr == 'partielle':
            # Au moins un champ coïncide, mais ni rattaché ni nom complet.
            qs = qs.filter(
                ligne_eligibilite__isnull=True, corresp_nom_complet=False,
            ).filter(
                Q(corresp_code=True) | Q(corresp_f_nom=True)
                | Q(corresp_f_postnom=True) | Q(corresp_f_prenom=True)
            )
        elif corr == 'aucune':
            qs = qs.filter(
                ligne_eligibilite__isnull=True, corresp_nom_complet=False,
                corresp_code=False, corresp_f_nom=False,
                corresp_f_postnom=False, corresp_f_prenom=False,
            )

        # Filtre « doublons uniquement » : dossiers ayant au moins un jumeau.
        if self.request.query_params.get('doublons') in ('1', 'true', 'oui'):
            qs = qs.filter(a_doublon=True)

        # Recherche tolérante par nom (accents/casse/ordre indifférents) OU par code.
        q = self.request.query_params.get('q', '').strip()
        if q:
            tokens = tokens_recherche(q)
            if tokens:
                nom_q = Q()
                for token in tokens:
                    nom_q &= Q(texte_recherche__contains=token)
                qs = qs.filter(nom_q | Q(code__icontains=q))
            else:
                qs = qs.filter(code__icontains=q)

        # Tri demandé par le tableau (sinon : plus récents d'abord).
        ordering = self.request.query_params.get('ordering', '')
        if ordering.lstrip('-') in self.TRI_AUTORISE:
            qs = qs.order_by(ordering)
        else:
            qs = qs.order_by('-cree_le')
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
        # Candidatures ouvertes uniquement : pas de dépôt sur un appel clôturé
        # (ou non publié). Garde-fou serveur, en plus du masquage côté front.
        if not appel.est_ouvert:
            raise ValidationError(
                "Les candidatures pour cet appel sont clôturées."
            )
        # Appel à candidature unique : un seul dossier par compte.
        if appel.candidature_unique and appel.dossiers.filter(deposant=user).exists():
            raise ValidationError(
                "Vous avez déjà une candidature pour cet appel : une seule est autorisée."
            )
        # Anti-doublon : un seul brouillon à la fois par appel et par compte.
        # Règle applicative à la création uniquement (pas de contrainte en
        # base) : les brouillons multiples existants restent valides.
        if appel.dossiers.filter(
            deposant=user, statut=Dossier.Statut.BROUILLON,
        ).exists():
            raise ValidationError(
                "Vous avez déjà un dossier en brouillon pour cet appel. "
                "Reprenez-le depuis « Mes dossiers » (ou supprimez-le) "
                "avant d'en créer un nouveau."
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

    @action(detail=True, methods=['patch'], url_path='identite')
    def modifier_identite(self, request, pk=None):
        """Corrige l'identité d'un dossier : code, nom, postnom, prénom.

        Réservé aux administrateurs et correcteurs ; possible quel que soit le
        statut (sert à corriger une coquille après dépôt). `texte_recherche` est
        recalculé automatiquement (recherche/doublons cohérents).
        """
        if not (roles.est_admin(request.user) or roles.est_correcteur(request.user)):
            raise PermissionDenied(
                "Seuls les administrateurs et correcteurs peuvent modifier l'identité."
            )
        dossier = self.get_object()
        serializer = ModificationIdentiteSerializer(dossier, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(self.get_serializer(dossier).data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Comptes de dossiers par statut (scopés par rôle), pour les KPI.

        Reprend le scoping de `get_queryset` mais sans le filtre `statut`, afin
        de fournir les totaux de chaque statut en une seule requête.
        """
        user = request.user
        qs = Dossier.objects.all()
        if roles.acces_backoffice(user):
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

    @action(detail=False, methods=['get'], url_path='doublon-suivant')
    def doublon_suivant(self, request):
        """Prochain dossier DÉPOSÉ ayant un doublon, pour balayer les doublons.

        `?apres=<id>` : renvoie le suivant (id croissant) ; boucle au début sinon.
        `?appel=<id>` : restreint à un appel. Renvoie {id, total}.
        """
        if not roles.acces_backoffice(request.user):
            raise PermissionDenied("Réservé au back-office.")
        base = (
            Dossier.objects
            .filter(statut=Dossier.Statut.DEPOSE)
            .annotate(a_doublon=self._doublon_exists())
            .filter(a_doublon=True)
            .order_by('id')
        )
        appel = request.query_params.get('appel')
        if appel:
            base = base.filter(appel_id=appel)
        total = base.count()
        apres = request.query_params.get('apres')
        suivant = base.filter(id__gt=apres).first() if apres else None
        if suivant is None:
            suivant = base.first()   # boucle au début
        return Response({'id': suivant.id if suivant else None, 'total': total})

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
        """Téléchargement protégé d'une pièce (jamais d'URL publique).

        `?inline=1` sert le fichier en ligne (aperçu PDF/image dans l'app) au
        lieu de forcer le téléchargement.
        """
        dossier = self.get_object()  # déjà scopé par rôle/propriété
        piece = get_object_or_404(PieceJointe, pk=piece_id, dossier=dossier)
        try:
            fichier = piece.fichier.open('rb')
        except FileNotFoundError as exc:
            raise Http404("Fichier introuvable.") from exc
        inline = request.query_params.get('inline') in ('1', 'true', 'oui')
        reponse = FileResponse(fichier, as_attachment=not inline,
                               filename=piece.nom_original or 'piece')
        if inline:
            # Autorise l'affichage dans une iframe même origine (aperçu in-app).
            reponse['X-Frame-Options'] = 'SAMEORIGIN'
        return reponse

    @action(detail=True, methods=['post'])
    def soumettre(self, request, pk=None):
        """BROUILLON → DÉPOSÉ : verrouille le dossier si toutes les pièces

        obligatoires sont présentes, puis envoie l'accusé de réception.
        """
        dossier = self.get_object()
        if dossier.deposant_id != request.user.id and not request.user.is_superuser:
            raise PermissionDenied("Ce dossier ne vous appartient pas.")
        # Candidatures clôturées entre la création du brouillon et sa soumission :
        # on refuse le dépôt (cohérent avec le masquage du bouton « Postuler »).
        if not dossier.appel.est_ouvert:
            raise ValidationError(
                {'detail': "Les candidatures pour cet appel sont clôturées."}
            )
        manquantes = dossier.pieces_obligatoires_manquantes()
        if manquantes:
            raise ValidationError({
                'pieces_manquantes': [tp.libelle for tp in manquantes],
                'detail': "Des pièces obligatoires sont manquantes.",
            })
        self._rattacher_par_nom(dossier)
        try:
            # Verrou : un double-clic sur « Soumettre » ne dépose qu'une fois
            # (le second relit le statut DÉPOSÉ et échoue sans second accusé).
            with transaction.atomic():
                dossier = Dossier.objects.select_for_update().get(pk=dossier.pk)
                dossier.changer_statut(
                    Dossier.Statut.DEPOSE, par=request.user,
                    motif='Soumission par le candidat',
                )
        except DjangoValidationError as exc:
            raise ValidationError({'detail': exc.messages})

        self._envoyer_accuse(dossier)
        return Response(self.get_serializer(dossier).data)

    @staticmethod
    def _rattacher_par_nom(dossier):
        """Rattache la ligne d'éligibilité qui désigne cette même personne.

        Critère = nom complet identique (nom ET postnom ET prénom ; cf.
        `Dossier.ligne_eligibilite_correspondante`), JAMAIS le code seul : des
        candidats saisissent le code d'autrui (triche). Best-effort : seulement
        si le dossier n'est pas déjà rattaché et si la correspondance est unique.
        """
        if dossier.ligne_eligibilite_id:
            return
        ligne = dossier.ligne_eligibilite_correspondante()
        if ligne:
            dossier.ligne_eligibilite = ligne
            dossier.save(update_fields=['ligne_eligibilite'])

    @staticmethod
    def _code_dossier(dossier):
        """Code du dossier pour l'affichage (emails, sujets) ; repli sur #id."""
        return dossier.code or f'#{dossier.pk}'

    def _envoyer_accuse(self, dossier):
        """Accusé de réception au candidat (best-effort : n'annule pas le dépôt)."""
        code = self._code_dossier(dossier)
        try:
            envoyer_email(
                destinataire=dossier.email,
                sujet=f'Accusé de réception — dossier {code}',
                template='accuse_reception.html',
                contexte={
                    'nom_candidat': f'{dossier.nom} {dossier.postnom} {dossier.prenom}'.strip(),
                    'code_dossier': code,
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

        # Verrou ligne par ligne : deux décisions simultanées sur le MÊME
        # dossier (double-clic, deux agents) se sérialisent ; la seconde relit
        # le statut à jour et échoue proprement si la transition est devenue
        # interdite. Ne touche jamais qu'un seul dossier (pk de l'URL).
        try:
            with transaction.atomic():
                dossier = Dossier.objects.select_for_update().get(pk=dossier.pk)
                if lier_eligibilite:
                    eid = request.data.get('eligibilite_id')
                    if eid:
                        ligne = get_object_or_404(ListeEligibilite, pk=eid)
                        dossier.ligne_eligibilite = ligne
                        dossier.save(update_fields=['ligne_eligibilite'])
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
                    'code_dossier': self._code_dossier(dossier),
                    'appel': dossier.appel.titre,
                    'motif': motif,
                },
            )
        except Exception:  # noqa: BLE001 — l'échec email ne casse pas la transition
            pass

    # --- Actions ADMIN (dossier DÉPOSÉ) ---------------------------------

    @action(detail=True, methods=['post'])
    def approuver(self, request, pk=None):
        """DÉPOSÉ → EN_EXAMEN (admin ou validateur). `eligibilite_id` optionnel.

        Aucun email pendant le traitement : les candidats retenus sont notifiés
        seulement à la publication de la liste (voir `publier_retenus`).
        """
        return self._transition(
            request, Dossier.Statut.EN_EXAMEN, roles.peut_traiter,
            lier_eligibilite=True,
        )

    @action(detail=True, methods=['post'])
    def rejeter(self, request, pk=None):
        """DÉPOSÉ → REJETÉ (admin ou validateur, motif obligatoire). Aucun email."""
        return self._transition(
            request, Dossier.Statut.REJETE, roles.peut_traiter,
            motif_obligatoire=True,
        )

    @action(detail=True, methods=['post'], url_path='rejeter-doublon')
    def rejeter_doublon(self, request, pk=None):
        """Rejette un dossier en double (DÉPOSÉ → REJETÉ), sans email.

        Raccourci pour traiter les doublons : motif « Dossier en double »
        pré-rempli, pas de notification au candidat.
        """
        if not roles.peut_traiter(request.user):
            raise PermissionDenied("Réservé aux administrateurs et validateurs.")
        dossier = self.get_object()
        try:
            with transaction.atomic():
                dossier = Dossier.objects.select_for_update().get(pk=dossier.pk)
                dossier.changer_statut(
                    Dossier.Statut.REJETE, par=request.user, motif='Dossier en double',
                )
        except DjangoValidationError as exc:
            raise ValidationError({'detail': exc.messages})
        return Response(self.get_serializer(dossier).data)

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
        """Qui peut trancher retenir/non-retenir : l'admin ou un validateur,
        ou un évaluateur désigné ET autorisé (peut_valider) sur ce dossier."""
        user = self.request.user
        if roles.peut_traiter(user):
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
            # Consultation des avis : tout le back-office, ou un désigné.
            if not roles.acces_backoffice(request.user):
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

    # Décision finale : l'admin ou un validateur tranche, ou un évaluateur
    # désigné autorisé (vérifié ensuite dossier par dossier).
    _peut_decider = staticmethod(
        lambda u: roles.peut_traiter(u) or roles.est_evaluateur(u)
    )

    @action(detail=True, methods=['post'])
    def retenir(self, request, pk=None):
        """EN_EXAMEN → RETENU (admin, ou évaluateur désigné et autorisé).

        Aucun email ici : le retenu est notifié à la publication de la liste.
        """
        return self._transition(
            request, Dossier.Statut.RETENU, self._peut_decider,
            verif_validateur=True,
        )

    @action(detail=True, methods=['post'], url_path='non-retenir')
    def non_retenir(self, request, pk=None):
        """EN_EXAMEN → NON_RETENU (admin ou évaluateur autorisé, motif requis).
        Aucun email (traitement)."""
        return self._transition(
            request, Dossier.Statut.NON_RETENU, self._peut_decider,
            motif_obligatoire=True, verif_validateur=True,
        )

    @action(detail=True, methods=['get'])
    def historique(self, request, pk=None):
        """Journal d'audit des changements de statut du dossier."""
        dossier = self.get_object()
        data = HistoriqueStatutSerializer(
            dossier.historique.all(), many=True,
        ).data
        return Response(data)


class ReclamationThrottle(AnonRateThrottle):
    """Limite le formulaire public de réclamation (anti-spam)."""

    scope = 'reclamation'


class ReclamationViewSet(viewsets.ModelViewSet):
    """Réclamations d'éligibilité (personne absente de la liste).

    - **création** : publique (sans compte), throttlée + honeypot ;
    - **liste / détail / actions / téléchargement** : réservés aux administrateurs.

    À la validation, un `Dossier` est créé et conduit jusqu'à RETENU via
    `Dossier.changer_statut()` (l'audit et l'invariant de statut sont préservés).
    """

    # 25 par page, taille ajustable (page_size) — comme la file de validation.
    pagination_class = PaginationStandard
    # Multipart pour la création (fichiers) ; JSON pour valider/rejeter.
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        if self.action == 'create':
            return ReclamationCreationSerializer
        return ReclamationAdminSerializer

    def get_permissions(self):
        return [AllowAny()] if self.action == 'create' else [IsAuthenticated()]

    def get_throttles(self):
        return [ReclamationThrottle()] if self.action == 'create' else []

    def get_queryset(self):
        # Hors création, l'accès est réservé au back-office (lecture ; les
        # actions valider/rejeter sont contrôlées séparément).
        if not roles.acces_backoffice(self.request.user):
            return ReclamationEligibilite.objects.none()
        qs = ReclamationEligibilite.objects.select_related(
            'appel', 'poste', 'traite_par', 'dossier_cree',
        ).prefetch_related('documents').annotate(
            # Doublon probable : une AUTRE réclamation du même appel, même nom
            # complet (normalisé), pas encore rejetée. Indicatif.
            a_doublon=Exists(
                ReclamationEligibilite.objects
                .filter(appel_id=OuterRef('appel_id'))
                .exclude(statut=ReclamationEligibilite.Statut.REJETEE)
                .exclude(texte_recherche='')
                .filter(texte_recherche=OuterRef('texte_recherche'))
                .exclude(pk=OuterRef('pk'))
            ),
            # Croisement : la personne a-t-elle DÉJÀ un dossier DÉPOSÉ (même nom
            # complet normalisé) ? Sa réclamation est alors redondante (elle est
            # déjà candidate). Par nom, jamais l'email (cf. règle anti-triche).
            a_dossier_depose=Exists(
                Dossier.objects
                .filter(statut=Dossier.Statut.DEPOSE)
                .exclude(texte_recherche='')
                .filter(texte_recherche=OuterRef('texte_recherche'))
            ),
        )
        statut = self.request.query_params.get('statut')
        if statut:
            qs = qs.filter(statut=statut)
        appel = self.request.query_params.get('appel')
        if appel:
            qs = qs.filter(appel_id=appel)
        if self.request.query_params.get('dossier_depose') in ('1', 'true', 'oui'):
            qs = qs.filter(a_dossier_depose=True)
        q = self.request.query_params.get('q')
        if q:
            for token in tokens_recherche(q):
                qs = qs.filter(texte_recherche__contains=token)
        return qs

    # Documents attendus : accusé, CV, pièce d'identité (un chacun) + diplôme(s).
    DOCS_SIMPLES = [
        ('accuse', DocumentReclamation.Type.ACCUSE, "l'accusé de réception"),
        ('cv', DocumentReclamation.Type.CV, 'le CV'),
        ('identite', DocumentReclamation.Type.IDENTITE, "la pièce d'identité"),
    ]

    def _valider_fichier(self, fichier, libelle):
        ext = fichier.name.rsplit('.', 1)[-1].lower() if '.' in fichier.name else ''
        if ext not in EXTENSIONS_AUTORISEES:
            raise ValidationError(
                {'detail': f"Format non autorisé pour {libelle} (acceptés : "
                           f"{', '.join(EXTENSIONS_AUTORISEES)})."}
            )
        if fichier.size > TAILLE_MAX_PIECE:
            limite = TAILLE_MAX_PIECE // (1024 * 1024)
            raise ValidationError({'detail': f"Fichier trop volumineux pour {libelle} (max {limite} Mo)."})

    def create(self, request, *args, **kwargs):
        """Dépôt public : valide texte + justificatifs, réponse neutre.

        Justificatifs requis : accusé de réception, CV, pièce d'identité (un
        chacun) et au moins un diplôme (plusieurs possibles).
        """
        serializer = self.get_serializer(data=request.data)
        # `validate_appel` (serializer) refuse déjà un appel non publié : la
        # réclamation est donc fermée en même temps que les candidatures.
        serializer.is_valid(raise_exception=True)

        # Collecte et validation des fichiers.
        simples = {}
        for champ, type_doc, libelle in self.DOCS_SIMPLES:
            fichier = request.FILES.get(champ)
            if not fichier:
                raise ValidationError({'detail': f"Veuillez joindre {libelle}."})
            self._valider_fichier(fichier, libelle)
            simples[type_doc] = fichier

        diplomes = request.FILES.getlist('diplomes')
        if not diplomes:
            raise ValidationError({'detail': "Veuillez joindre au moins un diplôme (ou équivalent)."})
        for d in diplomes:
            self._valider_fichier(d, 'un diplôme')

        with transaction.atomic():
            reclamation = serializer.save()
            for type_doc, fichier in simples.items():
                DocumentReclamation.objects.create(
                    reclamation=reclamation, type=type_doc, fichier=fichier,
                    nom_original=fichier.name[:255], taille=fichier.size,
                )
            for fichier in diplomes:
                DocumentReclamation.objects.create(
                    reclamation=reclamation, type=DocumentReclamation.Type.DIPLOME,
                    fichier=fichier, nom_original=fichier.name[:255], taille=fichier.size,
                )

        self._accuse_reception(reclamation)
        return Response(
            {'detail': "Votre réclamation a bien été enregistrée. "
                       "Vous recevrez une réponse par email."},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Comptes de réclamations par statut (back-office), pour les KPI."""
        if not roles.acces_backoffice(request.user):
            raise PermissionDenied("Réservé au back-office.")
        par_statut = {
            row['statut']: row['n']
            for row in ReclamationEligibilite.objects.values('statut').annotate(n=Count('id'))
        }
        return Response({'total': sum(par_statut.values()), 'par_statut': par_statut})

    @action(detail=True, methods=['get'])
    def doublons(self, request, pk=None):
        """Autres réclamations du même appel et même nom complet (non rejetées)."""
        if not roles.acces_backoffice(request.user):
            raise PermissionDenied("Réservé au back-office.")
        reclamation = self.get_object()
        if not reclamation.texte_recherche:
            return Response([])
        autres = (
            ReclamationEligibilite.objects
            .filter(appel_id=reclamation.appel_id, texte_recherche=reclamation.texte_recherche)
            .exclude(statut=ReclamationEligibilite.Statut.REJETEE)
            .exclude(pk=reclamation.pk)
            .order_by('cree_le')
        )
        return Response([
            {
                'id': r.id, 'nom': r.nom, 'postnom': r.postnom, 'prenom': r.prenom,
                'email': r.email, 'statut': r.statut,
                'statut_libelle': r.get_statut_display(), 'cree_le': r.cree_le,
            }
            for r in autres
        ])

    @action(detail=True, methods=['get'], url_path='dossiers-deposes')
    def dossiers_deposes(self, request, pk=None):
        """Dossiers DÉPOSÉS portant le même nom complet (personne déjà candidate).

        Sert à décider : si la personne a déjà un dossier déposé, sa réclamation
        est redondante et peut être rejetée. Rapprochement par nom (jamais email).
        """
        if not roles.acces_backoffice(request.user):
            raise PermissionDenied("Réservé au back-office.")
        reclamation = self.get_object()
        if not reclamation.texte_recherche:
            return Response([])
        dossiers = (
            Dossier.objects
            .filter(statut=Dossier.Statut.DEPOSE, texte_recherche=reclamation.texte_recherche)
            .select_related('appel', 'poste')
            .order_by('cree_le')
        )
        return Response([
            {
                'id': d.id, 'code': d.code, 'nom': d.nom, 'postnom': d.postnom,
                'prenom': d.prenom, 'statut': d.statut,
                'statut_libelle': d.get_statut_display(),
                'appel_titre': d.appel.titre,
                'poste_libelle': d.poste.libelle if d.poste else None,
                'cree_le': d.cree_le,
            }
            for d in dossiers
        ])

    @action(detail=False, methods=['get'], url_path='doublon-suivant')
    def doublon_suivant(self, request):
        """Prochaine réclamation EN ATTENTE ayant un doublon (pour les balayer).

        `?apres=<id>` renvoie la suivante ; boucle au début sinon. {id, total}.
        """
        if not roles.acces_backoffice(request.user):
            raise PermissionDenied("Réservé au back-office.")
        sous_req = (
            ReclamationEligibilite.objects
            .filter(appel_id=OuterRef('appel_id'))
            .exclude(statut=ReclamationEligibilite.Statut.REJETEE)
            .exclude(texte_recherche='')
            .filter(texte_recherche=OuterRef('texte_recherche'))
            .exclude(pk=OuterRef('pk'))
        )
        base = (
            ReclamationEligibilite.objects
            .filter(statut=ReclamationEligibilite.Statut.EN_ATTENTE)
            .annotate(a_doublon=Exists(sous_req))
            .filter(a_doublon=True)
            .order_by('id')
        )
        appel = request.query_params.get('appel')
        if appel:
            base = base.filter(appel_id=appel)
        total = base.count()
        apres = request.query_params.get('apres')
        suivant = base.filter(id__gt=apres).first() if apres else None
        if suivant is None:
            suivant = base.first()
        return Response({'id': suivant.id if suivant else None, 'total': total})

    @action(detail=True, methods=['get'],
            url_path=r'documents/(?P<doc_id>[^/.]+)')
    def telecharger_document(self, request, pk=None, doc_id=None):
        """Téléchargement protégé d'un justificatif (back-office ; jamais public)."""
        if not roles.acces_backoffice(request.user):
            raise PermissionDenied("Réservé au back-office.")
        reclamation = self.get_object()
        doc = get_object_or_404(DocumentReclamation, pk=doc_id, reclamation=reclamation)
        try:
            fichier = doc.fichier.open('rb')
        except FileNotFoundError as exc:
            raise Http404("Fichier introuvable.") from exc
        inline = request.query_params.get('inline') in ('1', 'true', 'oui')
        reponse = FileResponse(fichier, as_attachment=not inline,
                               filename=doc.nom_original or 'document')
        if inline:
            reponse['X-Frame-Options'] = 'SAMEORIGIN'
        return reponse

    @action(detail=True, methods=['post'])
    def valider(self, request, pk=None):
        """Valide la réclamation : crée un dossier et le conduit jusqu'à RETENU."""
        if not roles.peut_traiter(request.user):
            raise PermissionDenied("Réservé aux administrateurs et validateurs.")
        reclamation = self.get_object()

        # Poste : celui choisi par l'admin à la validation, sinon celui déclaré
        # par le réclamant dans le formulaire (absent sur les anciennes
        # réclamations, d'où le repli sur None).
        poste_id = request.data.get('poste_id')
        poste = get_object_or_404(Poste, pk=poste_id) if poste_id else reclamation.poste

        with transaction.atomic():
            # Verrou + re-contrôle du statut SOUS verrou : deux validations
            # simultanées de la même réclamation ne peuvent pas créer deux
            # dossiers — la seconde échoue avec « déjà traitée ».
            reclamation = (
                ReclamationEligibilite.objects
                .select_for_update().get(pk=reclamation.pk)
            )
            if reclamation.statut != ReclamationEligibilite.Statut.EN_ATTENTE:
                raise ValidationError("Cette réclamation a déjà été traitée.")
            dossier = Dossier.objects.create(
                appel=reclamation.appel, poste=poste, deposant=None,
                nom=reclamation.nom, postnom=reclamation.postnom,
                prenom=reclamation.prenom, email=reclamation.email,
                statut=Dossier.Statut.BROUILLON,
            )
            # Dossier issu d'une réclamation : exempté des pièces obligatoires
            # (l'accusé de réception tient lieu de justificatif). On enchaîne les
            # transitions pour conserver l'audit et respecter la machine à états.
            dossier.changer_statut(Dossier.Statut.DEPOSE, par=request.user,
                                   motif='Validé via réclamation (accusé de réception ACGT)')
            dossier.changer_statut(Dossier.Statut.EN_EXAMEN, par=request.user,
                                   motif='Validé via réclamation')
            dossier.changer_statut(Dossier.Statut.RETENU, par=request.user,
                                   motif='Validé via réclamation')
            reclamation.statut = ReclamationEligibilite.Statut.VALIDEE
            reclamation.traite_par = request.user
            reclamation.traite_le = timezone.now()
            reclamation.dossier_cree = dossier
            reclamation.save(update_fields=['statut', 'traite_par', 'traite_le', 'dossier_cree'])

        # Aucun email pendant le traitement : la personne (désormais RETENUE via
        # le dossier créé) sera notifiée à la publication de la liste.
        return Response(ReclamationAdminSerializer(reclamation).data)

    @action(detail=True, methods=['post'])
    def rejeter(self, request, pk=None):
        """Rejette la réclamation (motif obligatoire)."""
        if not roles.peut_traiter(request.user):
            raise PermissionDenied("Réservé aux administrateurs et validateurs.")
        reclamation = self.get_object()
        motif = (request.data.get('motif') or '').strip()
        if not motif:
            raise ValidationError({'motif': "Un motif est obligatoire."})

        with transaction.atomic():
            # Verrou + re-contrôle sous verrou (cf. `valider`) : un rejet ne
            # peut pas écraser une validation simultanée, et inversement.
            reclamation = (
                ReclamationEligibilite.objects
                .select_for_update().get(pk=reclamation.pk)
            )
            if reclamation.statut != ReclamationEligibilite.Statut.EN_ATTENTE:
                raise ValidationError("Cette réclamation a déjà été traitée.")
            reclamation.statut = ReclamationEligibilite.Statut.REJETEE
            reclamation.motif = motif
            reclamation.traite_par = request.user
            reclamation.traite_le = timezone.now()
            reclamation.save(update_fields=['statut', 'motif', 'traite_par', 'traite_le'])

        # Aucun email pendant le traitement (un rejet de réclamation ne notifie pas).
        return Response(ReclamationAdminSerializer(reclamation).data)

    # --- Emails (best-effort : n'annulent jamais l'opération) ----------

    def _accuse_reception(self, reclamation):
        try:
            envoyer_email(
                destinataire=reclamation.email,
                sujet='Accusé de réception de votre réclamation',
                template='reclamation_accuse.html',
                contexte={
                    'nom': f'{reclamation.nom} {reclamation.postnom} {reclamation.prenom}'.strip(),
                    'appel': reclamation.appel.titre,
                },
            )
        except Exception:  # noqa: BLE001
            pass

    def _notifier(self, reclamation, validee):
        sujet = ('Votre réclamation a été acceptée' if validee
                 else 'Décision concernant votre réclamation')
        template = 'reclamation_validee.html' if validee else 'reclamation_rejetee.html'
        try:
            envoyer_email(
                destinataire=reclamation.email,
                sujet=sujet,
                template=template,
                contexte={
                    'nom': f'{reclamation.nom} {reclamation.postnom} {reclamation.prenom}'.strip(),
                    'appel': reclamation.appel.titre,
                    'motif': reclamation.motif,
                },
            )
        except Exception:  # noqa: BLE001
            pass
