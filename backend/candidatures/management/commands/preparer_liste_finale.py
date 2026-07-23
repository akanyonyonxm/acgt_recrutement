"""Prépare (et publie) la liste FINALE des retenus à l'issue de l'interview.

Commande AUTONOME, à lancer MANUELLEMENT sur le serveur (jamais en CI). Ne
nécessite aucun fichier : les 79 retenus (dans l'ordre de la liste officielle)
sont intégrés ici.

Étapes (idempotentes, additives) :
  1. marque les retenus finaux PAR NOM (jamais par code), en conservant l'ordre
     de la liste (`final_ordre`) et le code de la définitive ;
  2. avec --publier : rend la liste finale publique — elle REMPLACE la liste des
     admis à l'interview sur la page publique /retenus.

Usage :
    python manage.py preparer_liste_finale --dry-run
    python manage.py preparer_liste_finale
    python manage.py preparer_liste_finale --publier
"""
from django.core.management.base import BaseCommand, CommandError

from candidatures.models import AppelCandidature, RetenuDefinitif
from candidatures.utils import normaliser_texte

# (nom, postnom, prénom) — ORDRE DE LA LISTE OFFICIELLE (par domaine, par rang).
FINAUX = [
    ('DIASOTUKA', 'WEFU', 'Chadrack'),
    ('PHEBE', 'MAKUNGA', 'Chris'),
    ('SIKI', 'GBIAMAGBEDE', 'Erick'),
    ('KOUTCHA', 'ZACHARIE', 'Benjamin'),
    ('KASONGA', 'KATALA', 'Arsel'),
    ('KOBALEMO', 'GBOMA', 'Horizon'),
    ('MAYELE', 'LEMBA', 'Dieuleveut'),
    ('LISSA', 'TEMO', 'LUC'),
    ('NYENGELE', 'NGINDU', 'Rachel'),
    ('LANDU', 'LUYEYE', 'Romuald'),
    ('KAMBERE', 'OTSHUDI', 'Donel'),
    ('MABANZA', 'MATABISI', 'Merci'),
    ('METRE', 'CONSTANTIN', 'BERLYSSE'),
    ('SIMON', 'SWEDI', 'Trésor'),
    ('AKSANTI', 'BALOLA', 'Jackson'),
    ('MPOMBO', 'BAKONGA', 'Fiston'),
    ('NGANDU', 'KANGOMBA', 'Patrick'),
    ('MWESHI', 'KYALONDAWA', 'Jonathan'),
    ('NZINGA', 'NDOSA', 'Issac'),
    ('KANDA', 'KALONJI', 'Dorea'),
    ('TUMWAKA', 'WATU', 'Elie'),
    ('ODIA', 'ILUNGA', 'Dorcas'),
    ('METRE', 'AMANI', 'Daniel'),
    ('KALONJI', 'KALONJI', 'Lucien'),
    ('KIALU', 'KALONJI', 'John'),
    ('NLEMVO', 'MALUNDAMA', 'NOE'),
    ('TSHIBAND', 'KASHAL', 'JUNIOR'),
    ('LUBEMBA', 'FUAMBA', 'Jures'),
    ('CILUMBU', 'CINGUTA', 'Shekina'),
    ('TAMBWE', 'MUTUNGU', '--'),
    ('MUTOMBO', 'KABEYA', 'Ephrem junior'),
    ('MALUMA', 'KAPESA', 'Christ'),
    ('KUYIBUKA', 'YAAV', 'Samuel'),
    ('BASILUA', 'MBOMBI', 'Glodi'),
    ('KUKAMBISA', 'SONIKA', 'Parfait'),
    ('PHAMBU', 'PFUTI', 'Abel'),
    ('KANGUDIA', 'MBUYI', 'Patient'),
    ('YODI', 'DJELA', 'Mays'),
    ('EBENGO', 'WOKIKI', 'Christian'),
    ('KONGOL', 'A MUKENG', 'Caleb'),
    ('MUKUNA', 'KATAKU', 'Princesse'),
    ('KABWANGALA', 'KHABA', 'Nestorine'),
    ('MUKENDI', 'TSHIPETA', 'Gedeon'),
    ('LANDU', 'BULENDOLO', 'Silver'),
    ('BUKASA', 'MUNYOKA', 'Bertrand'),
    ('KASONGA', 'NEDI', 'Michel'),
    ('LIKEKE', 'MBELA', 'Emmanuel'),
    ('CHIKURU', 'CENTWALI', 'Fidele'),
    ('MPOVA', 'MAGUA', 'Exauce'),
    ('TSHIVUADI', 'MUTANDA', 'Thomas'),
    ('ABELI', 'KYENENGWA', 'Leon'),
    ('YAMBENGA', 'KILONDO', 'Yams'),
    ('MBUKULU', 'TUVELELA', 'Louange'),
    ('ISSA', 'ELECA', 'Nathan'),
    ('MBOM', 'MBAKA', 'Georges'),
    ('IPALA', 'TAA’MBAK', 'Richard'),
    ('BAKABIKA', 'BIYELA', 'Audry'),
    ('KAYUMBA', 'KALONJI', 'Elie'),
    ('MWAIYANGA', 'NGBANGA', 'Maurice'),
    ('KABWE', 'BISEBA', 'Evardy'),
    ('KIMBUMBA', 'OTE-A-YIM', 'Gracia'),
    ('KIBUSU', 'NKALE', 'Glody'),
    ('AKONKWA', 'KAVUHA', 'Bertin'),
    ('MAMBA', 'KALAMBA', 'Jean'),
    ('NTUMBA', 'CIALA', 'Aaron'),
    ('MWEZE', 'NGOY', 'Daniel'),
    ('YIMBA', 'BAYIKIDI', 'Graddy'),
    ('MIAFUKAMA', 'DIZA', 'Emmanuel Grace'),
    ('MBUDI', 'TSHINGANA', 'John'),
    ('KALALA', 'TSHITENGE', 'Grace'),
    ('MATONDO', 'NDAYA', 'Rey'),
    ('TUNDULA', 'PENE-DIKONDO', 'Simon'),
    ('SUMBA', 'MALY', 'Boaz'),
    ('KABENA', 'MUTAMBA', 'Schadrack'),
    ('MALUDAMA', 'PEDRO', 'GRACE'),
    ('ZENGA', 'MAKENGELE', 'Joel'),
    ('TASA', 'OTSHUDIEMA', 'Einstein'),
    ('KAWENDE', 'MIOMA', 'Aston'),
    ('MUSHAGASHA', 'MUNGANGA', 'Jackson'),
]


class Command(BaseCommand):
    help = "Prépare/publie la liste finale des retenus (autonome, manuel)."

    def add_arguments(self, parser):
        parser.add_argument('--appel', type=int, default=None)
        parser.add_argument('--publier', action='store_true',
                            help="Publie la liste finale (remplace l'interview sur la page publique).")
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **opts):
        appel = self._appel(opts.get('appel'))
        dry = opts.get('dry_run')
        self.stdout.write(self.style.WARNING(
            f"Appel : « {appel.titre} » (id {appel.id})" + (" [DRY-RUN]" if dry else "")))

        par_nom = {}
        for e in appel.retenus_definitifs.all():
            cle = e.texte_recherche or normaliser_texte(f'{e.nom} {e.postnom} {e.prenom}')
            par_nom.setdefault(cle, []).append(e)

        if not dry:
            appel.retenus_definitifs.update(retenu_final=False, final_ordre=0)
        marques, introuvables, a_maj, ordre = 0, [], [], 0
        for nom, postnom, prenom in FINAUX:
            cle = normaliser_texte(f'{nom} {postnom} {prenom}')
            entrees = par_nom.get(cle)
            if not entrees:
                introuvables.append((nom, postnom, prenom))
                continue
            ordre += 1
            for e in entrees:
                e.retenu_final = True
                e.final_ordre = ordre
                a_maj.append(e)
            marques += 1
        if not dry:
            RetenuDefinitif.objects.bulk_update(a_maj, ['retenu_final', 'final_ordre'])

        self.stdout.write(self.style.SUCCESS(
            f"\nRetenus finaux rattachés PAR NOM : {marques} / {len(FINAUX)}"))
        if introuvables:
            self.stdout.write(self.style.ERROR(f"⚠ Introuvables ({len(introuvables)}) :"))
            for nom, postnom, prenom in introuvables:
                self.stdout.write(f"   - {nom} {postnom} {prenom}")

        if opts.get('publier'):
            if introuvables:
                raise CommandError("Publication annulée : des personnes sont introuvables.")
            if not dry:
                appel.liste_finale_publiee = True
                appel.save(update_fields=['liste_finale_publiee'])
            self.stdout.write(self.style.SUCCESS("Liste finale PUBLIÉE (remplace l'interview)."))
        else:
            self.stdout.write("(Ajoutez --publier pour rendre la liste finale publique.)")

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
            raise CommandError("Plusieurs appels publiés. Précisez --appel <id>.")
        return publies[0]
