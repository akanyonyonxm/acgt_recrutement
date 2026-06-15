"""Endpoints d'authentification.

Connexion par session Django (cookie). Le front Vue récupère d'abord le cookie
CSRF via /api/auth/csrf/, puis envoie l'entête X-CSRFToken sur les requêtes POST
authentifiées.

Pour ne pas divulguer quels emails ont un compte, les endpoints « demande de
reset » et « renvoi de vérification » répondent toujours de façon neutre.
"""

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.models import Group
from django.db import models
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .emails import envoyer_reinitialisation, envoyer_verification
from .models import JetonEmail
from .serializers import (
    ROLES_ATTRIBUABLES,
    ConnexionSerializer,
    CreationAgentSerializer,
    DemandeResetSerializer,
    InscriptionSerializer,
    JetonSerializer,
    ModificationAgentSerializer,
    ReinitialisationSerializer,
    UserSerializer,
)

User = get_user_model()

# Réponse neutre commune aux endpoints qui ne doivent pas révéler l'existence
# d'un compte (anti-énumération d'emails).
_MSG_NEUTRE = {
    'detail': "Si un compte correspond à cet email, un message vient d'être envoyé."
}


@method_decorator(ensure_csrf_cookie, name='get')
class CsrfView(APIView):
    """Pose le cookie CSRF pour le front (à appeler au démarrage de l'app)."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response({'detail': 'Cookie CSRF posé.'})


class InscriptionView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        # Inscription ouverte seulement pendant les candidatures (au moins un
        # appel publié). Sinon, refus net (la connexion reste possible pour les
        # comptes existants). Garde-fou serveur, en plus du masquage côté front.
        from candidatures.models import AppelCandidature

        if not AppelCandidature.objects.filter(
            statut=AppelCandidature.Statut.PUBLIE,
        ).exists():
            return Response(
                {'detail': "Les inscriptions sont closes : aucune candidature "
                           "n'est ouverte actuellement."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = InscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        utilisateur = serializer.save()
        # Best-effort : un échec d'envoi (ex. domaine non vérifié) ne doit pas
        # faire échouer la création du compte. Le candidat peut redemander le
        # mail via /auth/renvoyer-verification/.
        envoi_ok = True
        try:
            envoyer_verification(utilisateur)
        except Exception:  # noqa: BLE001
            envoi_ok = False
        return Response(
            {
                'detail': "Compte créé. Vérifiez votre email pour l'activer."
                if envoi_ok else
                "Compte créé, mais l'email d'activation n'a pas pu être envoyé. "
                "Réessayez l'envoi ou contactez le secrétariat.",
                'email_envoye': envoi_ok,
            },
            status=status.HTTP_201_CREATED,
        )


class VerifierEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = JetonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        jeton = (
            JetonEmail.objects
            .filter(jeton=serializer.validated_data['jeton'],
                    usage=JetonEmail.Usage.VERIFICATION)
            .select_related('utilisateur')
            .first()
        )
        if not jeton or not jeton.est_valide:
            return Response(
                {'detail': 'Lien de vérification invalide ou expiré.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        utilisateur = jeton.utilisateur
        utilisateur.email_verifie = True
        utilisateur.save(update_fields=['email_verifie'])
        jeton.consommer()
        return Response({'detail': 'Votre email est vérifié. Vous pouvez vous connecter.'})


class RenvoyerVerificationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = DemandeResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        utilisateur = User.objects.filter(
            email__iexact=serializer.validated_data['email'],
            email_verifie=False,
        ).first()
        if utilisateur:
            envoyer_verification(utilisateur)
        return Response(_MSG_NEUTRE)


class ConnexionView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ConnexionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        utilisateur = authenticate(
            request,
            username=serializer.validated_data['email'],
            password=serializer.validated_data['mot_de_passe'],
        )
        if utilisateur is None:
            return Response(
                {'detail': 'Email ou mot de passe incorrect.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        login(request, utilisateur)
        return Response(UserSerializer(utilisateur).data)


class DeconnexionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({'detail': 'Déconnecté.'})


class MoiView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class ListeEvaluateursView(APIView):
    """Liste des évaluateurs — pour la désignation sur un dossier.

    Lecture ouverte au back-office (noms/emails des évaluateurs) ; la
    désignation elle-même reste réservée aux administrateurs (côté dossiers).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from candidatures import roles

        if not roles.acces_backoffice(request.user):
            return Response(
                {'detail': "Réservé au back-office."},
                status=status.HTTP_403_FORBIDDEN,
            )
        evaluateurs = (
            User.objects
            .filter(groups__name=roles.GROUPE_EVALUATEUR)
            .order_by('first_name', 'email')
        )
        return Response([
            {'id': u.id, 'email': u.email,
             'nom': f'{u.first_name} {u.last_name}'.strip() or u.email}
            for u in evaluateurs
        ])


class GestionUtilisateursView(APIView):
    """Gestion des comptes agents du back-office (admin uniquement).

    GET  : liste les comptes ayant un rôle back-office (+ superusers).
    POST : crée un compte agent { email, prenom, nom, mot_de_passe, role }.

    Les candidats auto-inscrits n'apparaissent pas ici : cette page sert à
    donner accès à l'application de traitement (lecture seule, validation,
    correction, administration), pas à gérer les candidats.
    """

    permission_classes = [IsAuthenticated]

    def _verifier_admin(self, request):
        from candidatures import roles

        if not roles.est_admin(request.user):
            raise PermissionDenied("Réservé aux administrateurs.")

    @staticmethod
    def _serialiser(u):
        return {
            'id': u.id,
            'email': u.email,
            'prenom': u.first_name,
            'nom': u.last_name,
            'roles': UserSerializer().get_roles(u),
            'est_actif': u.is_active,
            'est_superuser': u.is_superuser,
            'derniere_connexion': u.last_login,
        }

    def get(self, request):
        # Lecture ouverte à la supervision (besoin de la liste pour répartir la
        # charge) ; la création/modification de comptes reste réservée à l'admin.
        from candidatures import roles

        if not roles.peut_superviser(request.user):
            raise PermissionDenied("Réservé aux administrateurs et superviseurs.")
        agents = (
            User.objects
            .filter(
                models.Q(is_superuser=True)
                | models.Q(groups__name__in=list(ROLES_ATTRIBUABLES.values()))
            )
            .distinct()
            .prefetch_related('groups')
            .order_by('first_name', 'last_name', 'email')
        )
        return Response([self._serialiser(u) for u in agents])

    def post(self, request):
        self._verifier_admin(request)
        serializer = CreationAgentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        utilisateur = User.objects.create_user(
            email=d['email'],
            password=d['mot_de_passe'],
            first_name=d.get('prenom', ''),
            last_name=d.get('nom', ''),
            email_verifie=True,  # compte créé par l'admin : pas de vérification
        )
        groupe = Group.objects.get(name=ROLES_ATTRIBUABLES[d['role']])
        utilisateur.groups.add(groupe)
        return Response(self._serialiser(utilisateur), status=status.HTTP_201_CREATED)


class GestionUtilisateurDetailView(APIView):
    """Modification d'un compte agent (admin) : rôle, actif/inactif, mot de passe.

    Garde-fous : on ne modifie ni un superuser (compte technique) ni son
    propre compte (pour ne pas se retirer l'accès ou se désactiver soi-même).
    """

    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        from candidatures import roles

        if not roles.est_admin(request.user):
            raise PermissionDenied("Réservé aux administrateurs.")
        utilisateur = get_object_or_404(User, pk=pk)
        if utilisateur.is_superuser:
            raise PermissionDenied(
                "Ce compte technique (superuser) ne se modifie pas ici."
            )
        if utilisateur.pk == request.user.pk:
            raise PermissionDenied(
                "Vous ne pouvez pas modifier votre propre compte "
                "(demandez à un autre administrateur)."
            )

        serializer = ModificationAgentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        if 'role' in d:
            # Un seul rôle back-office à la fois : on remplace les groupes de
            # rôle par le nouveau (les autres groupes éventuels sont conservés).
            groupes_roles = Group.objects.filter(name__in=list(ROLES_ATTRIBUABLES.values()))
            utilisateur.groups.remove(*groupes_roles)
            utilisateur.groups.add(Group.objects.get(name=ROLES_ATTRIBUABLES[d['role']]))
        if 'est_actif' in d:
            utilisateur.is_active = d['est_actif']
            utilisateur.save(update_fields=['is_active'])
        if d.get('mot_de_passe'):
            utilisateur.set_password(d['mot_de_passe'])
            utilisateur.save(update_fields=['password'])

        return Response(GestionUtilisateursView._serialiser(utilisateur))


class DemandeResetView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = DemandeResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        utilisateur = User.objects.filter(
            email__iexact=serializer.validated_data['email'],
        ).first()
        if utilisateur:
            envoyer_reinitialisation(utilisateur)
        return Response(_MSG_NEUTRE)


class ReinitialiserView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ReinitialisationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        jeton = (
            JetonEmail.objects
            .filter(jeton=serializer.validated_data['jeton'],
                    usage=JetonEmail.Usage.REINITIALISATION)
            .select_related('utilisateur')
            .first()
        )
        if not jeton or not jeton.est_valide:
            return Response(
                {'detail': 'Lien de réinitialisation invalide ou expiré.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        utilisateur = jeton.utilisateur
        utilisateur.set_password(serializer.validated_data['nouveau_mot_de_passe'])
        utilisateur.save(update_fields=['password'])
        jeton.consommer()
        return Response({'detail': 'Mot de passe réinitialisé. Vous pouvez vous connecter.'})
