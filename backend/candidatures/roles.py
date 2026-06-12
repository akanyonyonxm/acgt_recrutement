"""Rôles métier ACGT, portés par des groupes Django.

Groupes :
  - « Administrateurs » : valident l'éligibilité (approuver / rejeter)
  - « Évaluateurs »     : prononcent l'examen (retenir / non retenir)
  - « Correcteurs »     : corrigent l'identité d'un dossier (code, nom, postnom,
                          prénom) ; accès au back-office en consultation, mais
                          PAS de validation (réservée aux administrateurs).

Un superuser cumule tous les droits.
"""

GROUPE_ADMIN = 'Administrateurs'
GROUPE_EVALUATEUR = 'Évaluateurs'
GROUPE_CORRECTEUR = 'Correcteurs'


def est_admin(user):
    return user.is_superuser or user.groups.filter(name=GROUPE_ADMIN).exists()


def est_evaluateur(user):
    return user.is_superuser or user.groups.filter(name=GROUPE_EVALUATEUR).exists()


def est_correcteur(user):
    """Peut corriger l'identité d'un dossier. Les administrateurs le peuvent
    aussi (ils cumulent), via le contrôle `est_admin or est_correcteur`."""
    return user.is_superuser or user.groups.filter(name=GROUPE_CORRECTEUR).exists()
