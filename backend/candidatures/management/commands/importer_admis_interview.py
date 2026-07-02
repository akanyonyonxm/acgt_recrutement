"""Marque les ADMIS À L'INTERVIEW à partir du fichier Excel de publication.

À lancer MANUELLEMENT (jamais en CI). Opération additive et idempotente :

- lit toutes les feuilles par domaine (toutes SAUF « Liste définitive ») ;
- rattache chaque personne PAR NOM (nom+postnom+prénom normalisés) à une entrée
  déjà présente dans la liste définitive de l'appel (anti-triche : jamais par
  code, le code de l'Excel étant une numérotation propre non fiable) ;
- pose `admis_interview = True` sur les entrées trouvées ;
- ne CRÉE jamais d'entrée : une personne absente de la définitive est signalée
  (à traiter à part), pas ajoutée.

Le code affiché reste celui de la liste définitive. La publication se fait
ensuite via l'action « publier la liste des admis à l'interview ».

Usage :
    python manage.py importer_admis_interview docs/Liste_Publication_02.07.2026.xlsx
    python manage.py importer_admis_interview <fichier.xlsx> --appel 2 --dry-run
    python manage.py importer_admis_interview <fichier.xlsx> --reset   # remet tout à zéro d'abord
"""
from django.core.management.base import BaseCommand, CommandError

from candidatures.models import AppelCandidature, RetenuDefinitif
from candidatures.utils import normaliser_texte

FEUILLE_SOURCE = 'Liste définitive'  # feuille à IGNORER (c'est la liste complète)


class Command(BaseCommand):
    help = "Marque les admis à l'interview depuis l'Excel de publication (manuel, par nom)."

    def add_arguments(self, parser):
        parser.add_argument('fichier', help="Chemin du fichier .xlsx de publication.")
        parser.add_argument('--appel', type=int, default=None,
                            help="Id de l'appel (sinon : l'appel dont la liste définitive est publiée).")
        parser.add_argument('--reset', action='store_true',
                            help="Remet admis_interview=False sur tout l'appel avant l'import.")
        parser.add_argument('--dry-run', action='store_true',
                            help="Simulation : n'écrit rien.")

    def handle(self, *args, **opts):
        try:
            import openpyxl
        except ImportError:
            raise CommandError("openpyxl est requis (pip install openpyxl).")

        appel = self._appel(opts.get('appel'))
        dry = opts.get('dry_run')

        # Index de la liste définitive de l'appel, par nom normalisé.
        par_nom = {}
        for e in appel.retenus_definitifs.all():
            cle = e.texte_recherche or normaliser_texte(f'{e.nom} {e.postnom} {e.prenom}')
            par_nom.setdefault(cle, []).append(e)

        self.stdout.write(self.style.WARNING(
            f"Appel : « {appel.titre} » (id {appel.id}) — {len(par_nom)} personnes dans la définitive"))
        if dry:
            self.stdout.write(self.style.WARNING('  [DRY-RUN] aucune écriture'))

        try:
            wb = openpyxl.load_workbook(opts['fichier'], data_only=True)
        except FileNotFoundError:
            raise CommandError(f"Fichier introuvable : {opts['fichier']}")

        # Personnes de l'interview (toutes feuilles sauf la source), dédupliquées.
        vus, cibles, doublons_fichier = set(), [], 0
        for ws in wb.worksheets:
            if ws.title.strip().lower() == FEUILLE_SOURCE.lower():
                continue
            for row in ws.iter_rows(min_row=2, values_only=True):
                r = list(row)[:4]
                if not any(c is not None and str(c).strip() for c in r):
                    continue
                nom, postnom, prenom = r[1], r[2], r[3]
                cle = normaliser_texte(f'{nom or ""} {postnom or ""} {prenom or ""}')
                if not cle:
                    continue
                if cle in vus:
                    doublons_fichier += 1
                    continue
                vus.add(cle)
                cibles.append((ws.title, nom, postnom, prenom, cle))

        # Reset éventuel
        deja = appel.retenus_definitifs.filter(admis_interview=True).count()
        if opts.get('reset') and not dry:
            appel.retenus_definitifs.update(admis_interview=False, interview_ordre=0)

        # On respecte l'ORDRE DU FICHIER : ordre = 1, 2, 3… dans l'ordre de
        # première apparition (feuille par feuille, ligne par ligne).
        marques, introuvables, a_maj, ordre = 0, [], [], 0
        for feuille, nom, postnom, prenom, cle in cibles:
            entrees = par_nom.get(cle)
            if not entrees:
                introuvables.append((feuille, nom, postnom, prenom))
                continue
            ordre += 1
            for e in entrees:
                e.admis_interview = True
                e.interview_ordre = ordre
                a_maj.append(e)
            marques += 1

        if not dry:
            RetenuDefinitif.objects.bulk_update(a_maj, ['admis_interview', 'interview_ordre'])

        self.stdout.write('')
        self.stdout.write(f"Personnes distinctes dans l'Excel (hors « {FEUILLE_SOURCE} ») : {len(cibles)}"
                          + (f"  (+{doublons_fichier} doublons ignorés)" if doublons_fichier else ''))
        self.stdout.write(self.style.SUCCESS(
            f"Rattachées PAR NOM à la définitive : {marques}"))
        if opts.get('reset'):
            self.stdout.write(f"(reset : {deja} marquage(s) précédent(s) effacé(s))")
        if introuvables:
            self.stdout.write(self.style.ERROR(
                f"\n⚠ {len(introuvables)} personne(s) de l'Excel INTROUVABLE(S) dans la définitive :"))
            for feuille, nom, postnom, prenom in introuvables:
                self.stdout.write(f"    [{feuille}] {nom} {postnom} {prenom}")
        total = appel.retenus_definitifs.filter(admis_interview=True).count()
        self.stdout.write(self.style.SUCCESS(
            f"\n=== admis_interview dans l'appel : {total}"
            f"{' (simulation, inchangé)' if dry else ''} ==="))

    def _appel(self, appel_id):
        if appel_id:
            try:
                return AppelCandidature.objects.get(pk=appel_id)
            except AppelCandidature.DoesNotExist:
                raise CommandError(f"Aucun appel d'id {appel_id}.")
        publies = list(AppelCandidature.objects.filter(liste_definitive_publiee=True))
        if not publies:
            raise CommandError("Aucun appel avec une liste définitive publiée. Précisez --appel <id>.")
        if len(publies) > 1:
            ids = ', '.join(str(a.id) for a in publies)
            raise CommandError(f"Plusieurs appels publiés ({ids}). Précisez --appel <id>.")
        return publies[0]
