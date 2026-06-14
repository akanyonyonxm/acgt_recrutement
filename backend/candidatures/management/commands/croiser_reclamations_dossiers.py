"""Croise les réclamations d'éligibilité avec les dossiers DÉPOSÉS (par nom).

But : repérer les personnes présentes des DEUX côtés — quelqu'un qui a déposé un
dossier en ligne (statut DÉPOSÉ) **et** introduit une réclamation. Ces
réclamations sont en général redondantes (la personne est déjà candidate dans le
système) et peuvent être traitées en priorité.

Critère de rapprochement : nom complet identique (nom + postnom + prénom), via
`texte_recherche` (sans accents, minuscules, ordre indifférent) — le même
critère strict que le rattachement anti-triche. Jamais l'email (un proche peut
réutiliser une adresse).

Côté dossiers : on ne considère QUE les dossiers DÉPOSÉS (ni brouillon, ni déjà
traités). Côté réclamations : EN ATTENTE par défaut (option `--tous` pour toutes
les réclamations non rejetées).

Lecture seule (ne modifie rien). À lancer MANUELLEMENT.

  # En local (Windows) :
  venv/Scripts/python.exe manage.py croiser_reclamations_dossiers

  # En production (Docker) :
  docker compose -f docker-compose.prod.yml exec backend \\
      python manage.py croiser_reclamations_dossiers
"""

from django.core.management.base import BaseCommand

from candidatures.models import Dossier, ReclamationEligibilite


class Command(BaseCommand):
    help = ("Croise les réclamations (en attente) avec les dossiers déposés, "
            "par nom complet identique. Lecture seule.")

    def add_arguments(self, parser):
        parser.add_argument(
            '--tous', action='store_true',
            help="Considérer toutes les réclamations non rejetées "
                 "(par défaut : seulement EN ATTENTE).",
        )

    def handle(self, *args, **options):
        reclamations = ReclamationEligibilite.objects.exclude(texte_recherche='')
        if options['tous']:
            reclamations = reclamations.exclude(
                statut=ReclamationEligibilite.Statut.REJETEE,
            )
        else:
            reclamations = reclamations.filter(
                statut=ReclamationEligibilite.Statut.EN_ATTENTE,
            )
        reclamations = reclamations.order_by('nom', 'postnom', 'prenom')

        # Index des dossiers DÉPOSÉS par nom normalisé (une requête, pas de N+1).
        index = {}
        deposes = (
            Dossier.objects
            .filter(statut=Dossier.Statut.DEPOSE)
            .exclude(texte_recherche='')
        )
        for d in deposes:
            index.setdefault(d.texte_recherche, []).append(d)

        reclamations_avec_dossier = 0
        total_correspondances = 0

        for r in reclamations:
            dossiers = index.get(r.texte_recherche)
            if not dossiers:
                continue
            reclamations_avec_dossier += 1
            nom_r = f"{r.nom} {r.postnom} {r.prenom}".strip()
            self.stdout.write(
                f"RECLAMATION #{r.pk} [{r.statut}] {nom_r}  ({r.email})"
            )
            for d in dossiers:
                nom_d = f"{d.nom} {d.postnom} {d.prenom}".strip()
                self.stdout.write(
                    f"   ~ DOSSIER [{d.code or '-'}] {nom_d}  "
                    f"(depose le {d.cree_le:%d/%m/%Y})"
                )
                total_correspondances += 1
            self.stdout.write('')

        self.stdout.write(self.style.SUCCESS(
            f"Termine : {reclamations_avec_dossier} reclamation(s) correspondent "
            f"a un dossier depose (meme nom complet), "
            f"{total_correspondances} correspondance(s) au total."
        ))
