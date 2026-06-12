"""Liste les correspondances PARTIELLES dossier ↔ liste d'éligibilité.

Avec la règle de rattachement stricte (nom ET postnom ET prénom identiques),
certains dossiers ne sont pas rattachés automatiquement alors qu'il s'agit très
probablement de la même personne : il manque une lettre au prénom (coquille),
un champ est absent d'un côté, etc.

Cette commande liste, pour les dossiers NON rattachés, ceux dont le nom partage
avec une personne de la liste :
  - le même NOM **et** POSTNOM, ou
  - le même NOM **et** PRÉNOM,
en affichant côte à côte les noms complets et les codes, pour que l'admin
vérifie et rattache à la main depuis la fiche du dossier.

Lecture seule (ne modifie rien). À lancer MANUELLEMENT sur le serveur.

  python manage.py correspondances_a_verifier
"""

import operator
from functools import reduce

from django.core.management.base import BaseCommand
from django.db.models import Q

from candidatures.models import Dossier, ListeEligibilite


def _egal(a, b):
    return bool(a) and bool(b) and a.strip().lower() == b.strip().lower()


class Command(BaseCommand):
    help = ("Liste les dossiers non rattachés dont le nom partage 2 champs "
            "(nom+postnom ou nom+prénom) avec une personne de la liste.")

    def handle(self, *args, **options):
        total = 0
        dossiers_concernes = 0

        qs = (
            Dossier.objects
            .exclude(statut=Dossier.Statut.BROUILLON)
            .filter(ligne_eligibilite__isnull=True)
            .order_by('nom', 'postnom', 'prenom')
        )
        for d in qs:
            conds = []
            if d.nom and d.postnom:
                conds.append(Q(nom__iexact=d.nom) & Q(postnom__iexact=d.postnom))
            if d.nom and d.prenom:
                conds.append(Q(nom__iexact=d.nom) & Q(prenom__iexact=d.prenom))
            if not conds:
                continue

            lignes = list(ListeEligibilite.objects.filter(reduce(operator.or_, conds))[:5])
            trouve = False
            for ligne in lignes:
                # On ignore le match complet des 3 champs (déjà rattaché auto).
                if _egal(ligne.nom, d.nom) and _egal(ligne.postnom, d.postnom) \
                        and _egal(ligne.prenom, d.prenom):
                    continue
                criteres = []
                if _egal(ligne.nom, d.nom) and _egal(ligne.postnom, d.postnom):
                    criteres.append('nom+postnom')
                if _egal(ligne.nom, d.nom) and _egal(ligne.prenom, d.prenom):
                    criteres.append('nom+prenom')
                if not criteres:
                    continue

                gauche = f"#{d.pk} [{d.code or '-'}] {d.nom} {d.postnom} {d.prenom}".strip()
                droite = f"[{ligne.code or '-'}] {ligne.nom} {ligne.postnom} {ligne.prenom}".strip()
                if not trouve:
                    self.stdout.write(f"DOSSIER {gauche}")
                    trouve = True
                self.stdout.write(f"   ~ LISTE  {droite}   ({', '.join(criteres)})")
                total += 1

            if trouve:
                self.stdout.write('')
                dossiers_concernes += 1

        self.stdout.write(self.style.SUCCESS(
            f"Termine : {dossiers_concernes} dossier(s) a verifier, "
            f"{total} correspondance(s) partielle(s) au total."
        ))
