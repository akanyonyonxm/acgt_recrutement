"""Endpoints d'authentification.

Connexion par session Django (cookie). Le front Vue récupère d'abord le cookie
CSRF via /api/auth/csrf/, puis envoie l'entête X-CSRFToken sur les requêtes POST
authentifiées.

Pour ne pas divulguer quels emails ont un compte, les endpoints « demande de
reset » et « renvoi de vérification » répondent toujours de façon neutre.
"""

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .emails import envoyer_reinitialisation, envoyer_verification
from .models import JetonEmail
from .serializers import (
    ConnexionSerializer,
    DemandeResetSerializer,
    InscriptionSerializer,
    JetonSerializer,
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
    """Liste des évaluateurs (admin) — pour la désignation sur un dossier."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from candidatures import roles

        if not roles.est_admin(request.user):
            return Response(
                {'detail': "Réservé aux administrateurs."},
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
