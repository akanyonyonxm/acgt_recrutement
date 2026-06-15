"""Rôles métier ACGT, portés par des groupes Django.

Groupes :
  - « Administrateurs » : accès complet — valident, modifient les informations
                          (noms, codes), importent la liste, publient, gèrent
                          les comptes.
  - « Validateurs »     : traitent les dossiers et réclamations — font changer
                          les étapes (approuver / rejeter / retenir / non
                          retenir, valider / rejeter une réclamation). Ne
                          modifient PAS les informations (noms, codes).
  - « Correcteurs »     : corrigent l'identité d'un dossier (code, nom, postnom,
                          prénom) et les noms de la liste d'éligibilité ; accès
                          au back-office en consultation, mais PAS de validation.
  - « Lecteurs »        : back-office en LECTURE SEULE (dossiers, réclamations,
                          éligibilité, pièces, historique) — aucune action.
  - « Évaluateurs »     : prononcent l'examen des dossiers où ils sont désignés
                          (retenir / non retenir si autorisés).

Un superuser cumule tous les droits.
"""

GROUPE_ADMIN = 'Administrateurs'
GROUPE_EVALUATEUR = 'Évaluateurs'
GROUPE_CORRECTEUR = 'Correcteurs'
GROUPE_VALIDATEUR = 'Validateurs'
GROUPE_LECTEUR = 'Lecteurs'


def est_admin(user):
    return user.is_superuser or user.groups.filter(name=GROUPE_ADMIN).exists()


def est_evaluateur(user):
    return user.is_superuser or user.groups.filter(name=GROUPE_EVALUATEUR).exists()


def est_correcteur(user):
    """Peut corriger l'identité d'un dossier. Les administrateurs le peuvent
    aussi (ils cumulent), via le contrôle `est_admin or est_correcteur`."""
    return user.is_superuser or user.groups.filter(name=GROUPE_CORRECTEUR).exists()


def est_validateur(user):
    """Peut faire changer les étapes (dossiers + réclamations), sans pouvoir
    modifier les informations ni la configuration."""
    return user.is_superuser or user.groups.filter(name=GROUPE_VALIDATEUR).exists()


def est_lecteur(user):
    """Accès au back-office en lecture seule (aucune action)."""
    return user.is_superuser or user.groups.filter(name=GROUPE_LECTEUR).exists()


def acces_backoffice(user):
    """Visibilité back-office (tous les dossiers, réclamations, liste complète).

    Point de décision unique pour la CONSULTATION : tout rôle back-office voit
    tout ; ce que chacun peut FAIRE est contrôlé action par action
    (`peut_traiter`, `est_admin or est_correcteur`, `est_admin`)."""
    return (
        est_admin(user) or est_validateur(user)
        or est_correcteur(user) or est_lecteur(user)
    )


def peut_traiter(user):
    """Peut faire avancer un dossier ou une réclamation (changement d'étape)."""
    return est_admin(user) or est_validateur(user)


def peut_decider_affecte(user, affecte_a_id):
    """Peut trancher un élément (réclamation/dossier) selon l'affectation.

    Un administrateur peut toujours trancher (et réaffecter). Un validateur ne
    peut trancher que ce qui LUI est affecté — garantit qu'on ne traite jamais
    le lot d'un collègue. Les autres rôles (lecteur, correcteur) ne peuvent pas.
    """
    if est_admin(user):
        return True
    return est_validateur(user) and affecte_a_id == user.id
