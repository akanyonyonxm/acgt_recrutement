"""Rôles métier ACGT, portés par des groupes Django.

Deux groupes pilotent les transitions de statut :
  - « Administrateurs » : valident l'éligibilité (approuver / rejeter)
  - « Évaluateurs »     : prononcent l'examen (retenir / non retenir)

Un superuser cumule tous les droits.
"""

GROUPE_ADMIN = 'Administrateurs'
GROUPE_EVALUATEUR = 'Évaluateurs'


def est_admin(user):
    return user.is_superuser or user.groups.filter(name=GROUPE_ADMIN).exists()


def est_evaluateur(user):
    return user.is_superuser or user.groups.filter(name=GROUPE_EVALUATEUR).exists()
