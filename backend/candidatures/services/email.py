"""Service d'envoi d'emails — abstraction au-dessus de Resend.

Point d'entrée unique : `envoyer_email(...)`. Le reste du code (vérification de
compte, accusés de réception, notifications de statut) ne dépend que de cette
fonction, jamais de Resend directement. Ainsi on peut changer de fournisseur
sans toucher au métier.

Choix du backend, automatique :
  - `RESEND_API_KEY` défini  -> envoi réel via l'API HTTP Resend ;
  - sinon                    -> backend « console » (email affiché dans le
    terminal), pratique en développement et dans les tests.
"""

from __future__ import annotations

import logging

import httpx
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

RESEND_ENDPOINT = 'https://api.resend.com/emails'
TIMEOUT = 10.0


class EmailError(Exception):
    """Échec d'envoi d'un email (réseau, API Resend, etc.)."""


def _expediteur() -> str:
    """Adresse d'expédition formatée « Nom <email> »."""
    nom = getattr(settings, 'EMAIL_FROM_NOM', '').strip()
    adresse = settings.EMAIL_FROM
    return f'{nom} <{adresse}>' if nom else adresse


def _rendu(template: str, contexte: dict) -> str:
    """Rend un template d'email en HTML, avec le contexte de base enrichi."""
    base = {'site_nom': getattr(settings, 'SITE_NOM', '')}
    base.update(contexte or {})
    return render_to_string(f'emails/{template}', base)


def envoyer_email(
    destinataire: str,
    sujet: str,
    template: str,
    contexte: dict | None = None,
) -> None:
    """Envoie un email HTML rendu depuis un template Django.

    :param destinataire: adresse email du destinataire
    :param sujet: objet de l'email
    :param template: nom du fichier dans candidatures/templates/emails/
    :param contexte: variables passées au template
    :raises EmailError: si l'envoi réel échoue
    """
    html = _rendu(template, contexte or {})

    if not settings.RESEND_API_KEY:
        _envoyer_console(destinataire, sujet, html)
        return

    _envoyer_resend(destinataire, sujet, html)


def _envoyer_console(destinataire: str, sujet: str, html: str) -> None:
    """Backend de développement : journalise l'email au lieu de l'envoyer."""
    texte = strip_tags(html)
    logger.info(
        '[EMAIL CONSOLE] À: %s | Objet: %s\n%s', destinataire, sujet, texte,
    )
    # Aussi en sortie standard pour être visible pendant `runserver`.
    # flush=True : sinon la sortie reste bufferisée et n'apparaît pas tout de suite.
    print(
        f'\n----- EMAIL (console) -----\n'
        f'De      : {_expediteur()}\n'
        f'À       : {destinataire}\n'
        f'Objet   : {sujet}\n'
        f'---------------------------\n'
        f'{texte}\n'
        f'---------------------------\n',
        flush=True,
    )


def _envoyer_resend(destinataire: str, sujet: str, html: str) -> None:
    """Backend de production : appel HTTP à l'API Resend."""
    charge_utile = {
        'from': _expediteur(),
        'to': [destinataire],
        'subject': sujet,
        'html': html,
        # Version texte brut : meilleur score anti-spam qu'un email tout-HTML.
        'text': strip_tags(html),
    }
    # Reply-To vers une vraie boîte consultée (si configurée).
    reply_to = getattr(settings, 'EMAIL_REPLY_TO', '')
    if reply_to:
        charge_utile['reply_to'] = reply_to
    entetes = {
        'Authorization': f'Bearer {settings.RESEND_API_KEY}',
        'Content-Type': 'application/json',
    }
    try:
        reponse = httpx.post(
            RESEND_ENDPOINT, json=charge_utile, headers=entetes, timeout=TIMEOUT,
        )
        reponse.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.error(
            'Resend a refusé l\'email pour %s : %s — %s',
            destinataire, exc.response.status_code, exc.response.text,
        )
        raise EmailError(
            f'Resend a refusé l\'envoi ({exc.response.status_code}).'
        ) from exc
    except httpx.HTTPError as exc:
        logger.error('Erreur réseau lors de l\'envoi à %s : %s', destinataire, exc)
        raise EmailError('Erreur réseau lors de l\'envoi de l\'email.') from exc

    logger.info('Email envoyé à %s via Resend (objet: %s)', destinataire, sujet)
