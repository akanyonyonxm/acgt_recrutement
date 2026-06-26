"""Ajoute une liste SUPPLÉMENTAIRE de personnes admises à la liste DÉFINITIVE.

À lancer MANUELLEMENT sur le serveur (jamais en CI / entrypoint). Opération
additive et idempotente :

- les entrées sont créées dans `RetenuDefinitif` avec `origine = SUPPLEMENT` ;
- elles figurent sur la liste définitive (page publique + PDF + Excel) mais sont
  SANS dossier/recours source ;
- elles N'ENTRENT dans aucune statistique (RapportsView ne lit pas cette table) ;
- les CODES sont attribués À LA SUITE du dernier code définitif existant
  (max + 1), donc la liste déjà publiée et ses codes ne sont jamais touchés ;
- relancer la commande NE crée PAS de doublon (on saute toute personne dont le
  nom normalisé est déjà présent dans la liste définitive de l'appel).

La salle n'est PAS attribuée ici : utiliser ensuite « Affecter les salles » dans
le back-office (par ville) pour répartir, supplémentaires inclus.

Usage :
    python manage.py ajouter_retenus_supplementaires            # appel publié (auto)
    python manage.py ajouter_retenus_supplementaires --appel 19
    python manage.py ajouter_retenus_supplementaires --dry-run  # simulation
"""
from django.core.management.base import BaseCommand, CommandError

from candidatures.models import AppelCandidature, RetenuDefinitif
from candidatures.utils import normaliser_texte

V = RetenuDefinitif.Ville

# Personnes à ajouter (liste supplémentaire). Likasi est rattachée à Lubumbashi
# pour le site d'examen. Domaine = libellé libre affiché tel quel.
SUPPLEMENTAIRES = [
    # --- Liste supplémentaire (image 1) ---
    ('BOTOKO', 'IKEKA', 'ALAIN', 'Environnementaliste / Gestion', V.KINSHASA),
    ('KARNIB', 'DINZEY', 'BOVARY', 'Bâtiment et travaux publics', V.KINSHASA),
    ('KAYETU', 'KANYINDA', 'RACHETEE', 'Architecte', V.KINSHASA),
    ('LOKENDE', 'LUKUNDA', 'TONY', 'Environnementaliste', V.LUBUMBASHI),  # Likasi -> Lubumbashi
    ('MUNENE', 'CIBANVUNYA', 'FELICIEN', 'Bâtiment et travaux publics', V.KINSHASA),
    ('NGIAMA', 'KIMVUTA', 'Levieux', 'Bâtiment et travaux publics / PC', V.KINSHASA),
    ('NSIANA', 'MAKONKO', 'ARNAULD', 'Architecte', V.KINSHASA),
    ('NTUMBA', 'MUKEBA', 'ELYSEE', 'Architecte', V.KINSHASA),
    # --- Lubumbashi (image 2) ---
    ('MWAMBA', 'BANZE', 'CREDO', 'Architecte', V.LUBUMBASHI),
    ('EBUMA', 'GBENYE', 'JONATHAN', 'Environnementaliste', V.LUBUMBASHI),
    # --- Mbuji-Mayi (image 2) ---
    ('CILUMBU', 'CINGUTA', 'SHEKINA', 'Ingénieur civil', V.MBUJI_MAYI),
    ('MPOYI', 'TSHIMANDA', 'JONATHAN', 'Ingénieur civil', V.MBUJI_MAYI),
]


class Command(BaseCommand):
    help = "Ajoute la liste supplémentaire d'admis à la liste définitive (manuel, idempotent)."

    def add_arguments(self, parser):
        parser.add_argument('--appel', type=int, default=None,
                            help="Id de l'appel (sinon : l'appel dont la liste définitive est publiée).")
        parser.add_argument('--dry-run', action='store_true',
                            help='Simulation : affiche ce qui serait fait, sans rien écrire.')

    def handle(self, *args, **opts):
        appel = self._appel(opts.get('appel'))
        dry = opts.get('dry_run')

        existants = list(appel.retenus_definitifs.all())
        deja = {e.texte_recherche or normaliser_texte(f'{e.nom} {e.postnom} {e.prenom}')
                for e in existants}
        codes = [int(e.code) for e in existants if e.code.isdigit()]
        prochain = (max(codes) + 1) if codes else 1

        self.stdout.write(self.style.WARNING(
            f"Appel : « {appel.titre} » (id {appel.id})"))
        self.stdout.write(
            f"Entrées définitives existantes : {len(existants)} · "
            f"dernier code : {max(codes) if codes else '—'} · "
            f"prochain code : {prochain:04d}")
        if dry:
            self.stdout.write(self.style.WARNING('  [DRY-RUN] aucune écriture'))

        crees, sautes = 0, 0
        for nom, postnom, prenom, domaine, ville in SUPPLEMENTAIRES:
            tr = normaliser_texte(f'{nom} {postnom} {prenom}')
            if tr in deja:
                sautes += 1
                self.stdout.write(f"  = déjà présent, sauté : {nom} {postnom} {prenom}")
                continue
            code = f'{prochain:04d}'
            ligne = (f"  + {code}  {nom} {postnom} {prenom}  —  {domaine}  "
                     f"[{RetenuDefinitif.Ville(ville).label}]")
            if not dry:
                RetenuDefinitif.objects.create(
                    appel=appel, code=code, nom=nom, postnom=postnom, prenom=prenom,
                    poste_libelle=domaine, origine=RetenuDefinitif.Origine.SUPPLEMENT,
                    ville_examen=ville,
                )
            self.stdout.write(self.style.SUCCESS(ligne))
            deja.add(tr)
            prochain += 1
            crees += 1

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f"=== {crees} ajout(s){' (simulation)' if dry else ''}, {sautes} déjà présent(s) ==="))
        if crees and not dry:
            self.stdout.write(self.style.WARNING(
                "Pensez à relancer « Affecter les salles » (par ville) au back-office "
                "pour attribuer une salle aux nouveaux admis."))

    def _appel(self, appel_id):
        if appel_id:
            try:
                return AppelCandidature.objects.get(pk=appel_id)
            except AppelCandidature.DoesNotExist:
                raise CommandError(f"Aucun appel d'id {appel_id}.")
        publies = list(AppelCandidature.objects.filter(liste_definitive_publiee=True))
        if not publies:
            raise CommandError("Aucun appel avec une liste définitive publiée. "
                               "Précisez --appel <id>.")
        if len(publies) > 1:
            ids = ', '.join(str(a.id) for a in publies)
            raise CommandError(f"Plusieurs appels publiés ({ids}). Précisez --appel <id>.")
        return publies[0]
