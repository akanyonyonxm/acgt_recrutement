"""Emails liés au cycle de vie d'un compte (vérification, réinitialisation).

S'appuie sur le service générique candidatures.services.email : ici on se
contente de construire le lien front et de choisir le template.
"""

from django.conf import settings

from candidatures.services.email import envoyer_email

from .models import JetonEmail


def _lien(chemin: str, jeton) -> str:
    base = settings.FRONTEND_URL.rstrip('/')
    return f'{base}/{chemin}?jeton={jeton}'


def envoyer_verification(utilisateur):
    """Émet un jeton de vérification et envoie l'email d'activation."""
    jeton = JetonEmail.emettre(utilisateur, JetonEmail.Usage.VERIFICATION)
    envoyer_email(
        destinataire=utilisateur.email,
        sujet='Activez votre compte — ACGT Recrutement',
        template='verification_compte.html',
        contexte={
            'prenom': utilisateur.first_name,
            'lien_verification': _lien('candidat/verifier-email', jeton.jeton),
        },
    )
    return jeton


def envoyer_reinitialisation(utilisateur):
    """Émet un jeton de reset et envoie l'email de réinitialisation."""
    jeton = JetonEmail.emettre(utilisateur, JetonEmail.Usage.REINITIALISATION)
    envoyer_email(
        destinataire=utilisateur.email,
        sujet='Réinitialisez votre mot de passe — ACGT Recrutement',
        template='reinitialisation_mot_de_passe.html',
        contexte={
            'prenom': utilisateur.first_name,
            'lien_reset': _lien('candidat/reinitialiser-mot-de-passe', jeton.jeton),
        },
    )
    return jeton
