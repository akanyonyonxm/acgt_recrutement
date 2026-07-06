"""Prépare (et publie) la liste des ADMIS À L'INTERVIEW — commande AUTONOME.

À lancer MANUELLEMENT sur le serveur (jamais en CI). Ne nécessite AUCUN fichier :
la liste des 112 (dans l'ordre du fichier de publication) et les 2 corrections
de la définitive sont intégrées ici (données validées en local).

Étapes (toutes idempotentes, additives) :
  1. corrige 2 coquilles de la liste définitive (voir CORRECTIONS) ;
  2. marque les 112 admis à l'interview PAR NOM (jamais par code), en conservant
     l'ordre du fichier (`interview_ordre`) et le code de la définitive ;
  3. avec --publier : rend la liste interview publique (remplace l'affichage de
     la liste du test sur la page publique).

Usage :
    python manage.py preparer_liste_interview --dry-run
    python manage.py preparer_liste_interview
    python manage.py preparer_liste_interview --publier
"""
from django.core.management.base import BaseCommand, CommandError

from candidatures.models import AppelCandidature, RetenuDefinitif
from candidatures.utils import normaliser_texte

# Corrections de la définitive (coquilles constatées) : (code, champ, nouvelle valeur)
CORRECTIONS = [
    ('0571', 'postnom', 'MUTUNGU'),                    # TAMBWE : MUTUMU -> MUTUNGU
    ('0284', 'poste_libelle', 'Ingénieur électromécanicien'),  # LUMBALA MBUYI JOSUE : civil -> électromécanicien
]

# (nom, postnom, prénom, date ISO, heure d'arrivée) — ORDRE DU FICHIER.
INTERVIEW = [
    ('KOUTCHA', 'ZACHARIE', 'Benjamin', '2026-07-08', '08h45'),
    ('NGANDU', 'KANGOMBA', 'Patrick', '2026-07-08', '08h45'),
    ('KASONGA', 'KATALA', 'Arsel', '2026-07-08', '08h45'),
    ('PHEBE', 'MAKUNGA', 'CHRIS', '2026-07-08', '08h45'),
    ('DIASOTUKA', 'WEFU', 'CHADRACK', '2026-07-08', '08h45'),
    ('NYENGELE', 'NGINDU', 'Rachel', '2026-07-08', '08h45'),
    ('SIKI', 'GBIAMAGBEDE', 'Erick', '2026-07-08', '08h45'),
    ('TSHIBAND', 'KASHAL', 'JUNIOR', '2026-07-08', '08h45'),
    ('Kambere', 'Otshudi', 'Donel', '2026-07-08', '08h45'),
    ('LISSA', 'TEMO', 'LUC', '2026-07-08', '08h45'),
    ('SIMON', 'SWEDI', 'Trésor', '2026-07-08', '08h45'),
    ('AKSANTI', 'BALOLA', 'Jackson', '2026-07-08', '08h45'),
    ('MABANZA', 'MATABISI', 'Merci', '2026-07-08', '08h45'),
    ('TUMWAKA', 'WATU', 'Elie', '2026-07-08', '08h45'),
    ('KALONJI', 'KALONJI', 'Lucien', '2026-07-08', '08h45'),
    ('Landu', 'Luyeye', 'Romuald', '2026-07-08', '08h45'),
    ('MBOMBO', 'MUKENDI', 'JEREMIE', '2026-07-08', '08h45'),
    ('KOBALEMO', 'GBOMA', 'Horizon', '2026-07-08', '08h45'),
    ('Mayele', 'Lemba', 'Dieuleveut', '2026-07-08', '08h45'),
    ('Mpombo', 'Bakonga', 'Fiston', '2026-07-08', '08h45'),
    ('KUYIBUKA', 'YAAV', 'SAMUEL', '2026-07-08', '08h45'),
    ('Mutombo', 'Kabeya', 'EPHREM junior', '2026-07-08', '10h45'),
    ('KANDA', 'KALONJI', 'Dorea', '2026-07-08', '10h45'),
    ('MWESHI', 'KYALONDAWA', 'JONATHAN', '2026-07-08', '10h45'),
    ('KUMPI', 'LUZINGU', 'LE GERME', '2026-07-08', '10h45'),
    ('NZINGA', 'NDOSA', 'Issac', '2026-07-08', '10h45'),
    ('BASILUA', 'MBOMBI', 'GLODI', '2026-07-08', '10h45'),
    ('KIMONA', 'MUKOLO', 'JOHN', '2026-07-08', '10h45'),
    ('ODIA', 'ILUNGA', 'Dorcas', '2026-07-08', '08h45'),
    ('Simba', 'Mukanjila', 'Julien', '2026-07-08', '10h45'),
    ('BUKASA', 'MUNYOKA', 'BERTRAND', '2026-07-08', '08h45'),
    ('METRE', 'CONSTANTIN', 'BERLYSSE', '2026-07-08', '10h45'),
    ('CILUMBU', 'CINGUTA', 'SHEKINA', '2026-07-08', '10h45'),
    ('Bya’ene', 'Akulu', 'Jason', '2026-07-08', '10h45'),
    ('KAKULE', 'ESPERANT', 'JOSUE', '2026-07-08', '10h45'),
    ('Maluma', 'Kapesa', 'Christ', '2026-07-08', '10h45'),
    ('BULUMUKA', 'NTENSER', 'Sabin', '2026-07-08', '10h45'),
    ('MUKUNA', 'KATAKU', 'PRINCESSE', '2026-07-08', '10h45'),
    ('Sabihene', 'Masengo', 'Gloria', '2026-07-08', '10h45'),
    ('KABWANGALA', 'KHABA', 'NESTORINE', '2026-07-08', '10h45'),
    ('KIALU', 'KALONJI', 'John', '2026-07-08', '10h45'),
    ('LUBEMBA', 'FUAMBA', 'Jures', '2026-07-08', '10h45'),
    ('TAMBWE', 'MUTUNGU', '--', '2026-07-08', '10h45'),
    ('KANGUDIA', 'MBUYI', 'Patient', '2026-07-08', '08h45'),
    ('KUKAMBISA', 'SONIKA', 'Parfait', '2026-07-08', '12h45'),
    ('Landu', 'Bulendolo', 'Silver', '2026-07-08', '12h45'),
    ('Likeke', 'Mbela', 'Emmanuel', '2026-07-08', '12h45'),
    ('MUKENDI', 'TSHIPETA', 'Gedeon', '2026-07-08', '12h45'),
    ('CHIKURU', 'CENTWALI', 'Fidele', '2026-07-08', '12h45'),
    ('METRE', 'AMANI', 'Daniel', '2026-07-08', '12h45'),
    ('PHAMBU', 'PFUTI', 'Abel', '2026-07-08', '12h45'),
    ('Kamanga', 'Mbuyi', 'Eric', '2026-07-08', '12h45'),
    ('SOPI', 'LUEMBA', 'Nathan', '2026-07-08', '12h45'),
    ('KOLOKOTA', 'NDONGOMBE', 'Merdi', '2026-07-08', '12h45'),
    ('Mabibi', 'Ngedi', 'George', '2026-07-08', '12h45'),
    ('Mpova', 'Magua', 'Exauce', '2026-07-08', '12h45'),
    ('EBENGO', 'WOKIKI', 'Christian', '2026-07-08', '12h45'),
    ('KIANGANA', 'MAYEMBA', 'GILVANY', '2026-07-08', '12h45'),
    ('BITODI', 'LEYA', 'Jonathan', '2026-07-08', '12h45'),
    ('NLEMVO', 'MALUNDAMA', 'NOE', '2026-07-08', '12h45'),
    ('TSASA', 'TSASA', 'Kenedy', '2026-07-08', '12h45'),
    ('MBUKULU', 'TUVELELA', 'Louange', '2026-07-08', '12h45'),
    ('YAMBENGA', 'KILONDO', 'Yams', '2026-07-08', '12h45'),
    ('ABELI', 'KYENENGWA', 'LEON', '2026-07-08', '12h45'),
    ('KASONGA', 'NEDI', 'MICHEL', '2026-07-08', '14h45'),
    ('KONGOL', 'A MUKENG', 'Caleb', '2026-07-08', '14h45'),
    ('Labu', 'Mabanga', 'Elie', '2026-07-08', '14h45'),
    ('Tshivuadi', 'Mutanda', 'Thomas', '2026-07-08', '14h45'),
    ('BASHONGA', 'SHEMA', 'KETSIA', '2026-07-08', '14h45'),
    ('KARNIB', 'DINZEY', 'BOVARY', '2026-07-08', '14h45'),
    ('LUKUSA', 'CYUNZA', 'JEAN ESTIME', '2026-07-08', '14h45'),
    ('Meya', 'Ndamba', 'Hervé', '2026-07-08', '14h45'),
    ('WEMBOLENGA', 'OMALOKENGE', 'MICHAËL', '2026-07-08', '14h45'),
    ('YODI', 'DJELA', 'MAYS', '2026-07-08', '08h45'),
    ('ISSA', 'ELECA', 'Nathan', '2026-07-09', '07h45'),
    ('KIMBUMBA', 'OTE-A-YIM', 'Gracia', '2026-07-09', '07h45'),
    ('Mbom', 'Mbaka', 'Georges', '2026-07-09', '07h45'),
    ('IPALA', 'TAA’MBAK', 'Richard', '2026-07-09', '07h45'),
    ('BAKABIKA', 'BIYELA', 'AUDRY', '2026-07-09', '07h45'),
    ('Mwaiyanga', 'Ngbanga', 'Maurice', '2026-07-09', '07h45'),
    ('Kabwe', 'Biseba', 'Evardy', '2026-07-09', '07h45'),
    ('Kayumba', 'Kalonji', 'Elie', '2026-07-09', '07h45'),
    ('KIBUSU', 'NKALE', 'Glody', '2026-07-09', '07h45'),
    ('MIAFUKAMA', 'DIZA', 'EMMANUEL GRACE', '2026-07-09', '07h45'),
    ('MBUDI', 'TSHINGANA', 'JOHN', '2026-07-09', '07h45'),
    ('Ibalansimi', 'Ekenge', 'Marien', '2026-07-09', '07h45'),
    ('Bonkoy', 'Longonda', 'isaac', '2026-07-09', '07h45'),
    ('YIMBA', 'BAYIKIDI', 'Graddy', '2026-07-09', '07h45'),
    ('LUMBALA', 'MBUYI', 'JOSUE', '2026-07-09', '07h45'),
    ('AKONKWA', 'KAVUHA', 'Bertin', '2026-07-09', '07h45'),
    ('NTUMBA', 'CIALA', 'AARON', '2026-07-09', '07h45'),
    ('MAMBA', 'KALAMBA', 'Jean', '2026-07-09', '08h45'),
    ('Mweze', 'Ngoy', 'Daniel', '2026-07-09', '07h45'),
    ('SUMBA', 'MALY', 'BOAZ', '2026-07-10', '08h45'),
    ('KABENA', 'MUTAMBA', 'SCHADRACK', '2026-07-10', '08h45'),
    ('Lembalemba', 'Katawa', 'Willy', '2026-07-10', '07h45'),
    ('MATONA', 'MATONA', 'JONATHAN', '2026-07-10', '07h45'),
    ('LONGA', 'BUAKI', 'Benjamin', '2026-07-10', '07h45'),
    ('Zenga', 'Makengele', 'Joel', '2026-07-10', '07h45'),
    ('TUNDULA', 'PENE-DIKONDO', 'SIMON', '2026-07-10', '07h45'),
    ('MATONDO', 'NDAYA', 'Rey', '2026-07-10', '07h45'),
    ('LUMBALA', 'KAPETA', 'Aaron', '2026-07-10', '07h45'),
    ('MALUDAMA', 'PEDRO', 'GRACE', '2026-07-10', '07h45'),
    ('TASA', 'OTSHUDIEMA', 'Einstein', '2026-07-10', '07h45'),
    ('Kalala', 'Tshitenge', 'Grace', '2026-07-10', '07h45'),
    ('KALUNDA', '', 'Ludovic', '2026-07-10', '07h45'),
    ('Mutombo', 'Kabisa', 'Chancellevie', '2026-07-10', '07h45'),
    ('Tulu', 'Tulu', 'Norman', '2026-07-10', '07h45'),
    ('Mbuba', 'Shongo', 'Michee', '2026-07-10', '07h45'),
    ('NDOSIMAU', 'LUKAU', 'Christian', '2026-07-10', '07h45'),
    ('MUSHAGASHA', 'MUNGANGA', 'Jackson', '2026-07-10', '07h45'),
    ('Kawende', 'Mioma', 'Aston', '2026-07-10', '07h45'),
]


class Command(BaseCommand):
    help = "Prépare/publie la liste des admis à l'interview (autonome, manuel)."

    def add_arguments(self, parser):
        parser.add_argument('--appel', type=int, default=None)
        parser.add_argument('--publier', action='store_true',
                            help="Publie la liste interview (page publique).")
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **opts):
        appel = self._appel(opts.get('appel'))
        dry = opts.get('dry_run')
        self.stdout.write(self.style.WARNING(
            f"Appel : « {appel.titre} » (id {appel.id})" + (" [DRY-RUN]" if dry else "")))

        # Toutes les entrées en mémoire (les corrections y sont appliquées, même
        # en dry-run, pour que le matching reflète le résultat final).
        entrees = list(appel.retenus_definitifs.all())
        par_code = {e.code: e for e in entrees}

        # 1) Corrections de la définitive
        self.stdout.write("\n— Corrections de la définitive —")
        for code, champ, valeur in CORRECTIONS:
            e = par_code.get(code)
            if not e:
                self.stdout.write(self.style.ERROR(f"  ! code {code} introuvable"))
                continue
            actuel = getattr(e, champ)
            if actuel == valeur:
                self.stdout.write(f"  = {code} {champ} déjà « {valeur} »")
            else:
                self.stdout.write(self.style.SUCCESS(
                    f"  ~ {code} {champ} : « {actuel} » -> « {valeur} »"))
                setattr(e, champ, valeur)   # en mémoire (pour le matching)
                if not dry:
                    e.save()  # recalcule texte_recherche

        # 2) Marquage des 112 (par nom, ordre du fichier). La clé est recalculée
        #    depuis les valeurs COURANTES (corrections incluses).
        par_nom = {}
        for e in entrees:
            cle = normaliser_texte(f'{e.nom} {e.postnom} {e.prenom}')
            par_nom.setdefault(cle, []).append(e)

        from datetime import date as _date
        if not dry:
            appel.retenus_definitifs.update(admis_interview=False, interview_ordre=0,
                                            interview_date=None, interview_heure='')
        marques, introuvables, a_maj, ordre = 0, [], [], 0
        for nom, postnom, prenom, d_iso, heure in INTERVIEW:
            cle = normaliser_texte(f'{nom} {postnom} {prenom}')
            entrees = par_nom.get(cle)
            if not entrees:
                introuvables.append((nom, postnom, prenom))
                continue
            ordre += 1
            for e in entrees:
                e.admis_interview = True
                e.interview_ordre = ordre
                e.interview_date = _date.fromisoformat(d_iso) if d_iso else None
                e.interview_heure = heure or ''
                a_maj.append(e)
            marques += 1
        if not dry:
            RetenuDefinitif.objects.bulk_update(
                a_maj, ['admis_interview', 'interview_ordre', 'interview_date', 'interview_heure'])

        self.stdout.write(f"\n— Marquage interview —")
        self.stdout.write(self.style.SUCCESS(f"  Rattachés PAR NOM : {marques} / {len(INTERVIEW)}"))
        if introuvables:
            self.stdout.write(self.style.ERROR(f"  ⚠ Introuvables ({len(introuvables)}) :"))
            for nom, postnom, prenom in introuvables:
                self.stdout.write(f"     - {nom} {postnom} {prenom}")

        # 3) Publication
        if opts.get('publier'):
            self.stdout.write("\n— Publication —")
            if introuvables:
                raise CommandError("Publication annulée : des personnes sont introuvables (corrigez d'abord).")
            if not dry:
                appel.liste_interview_publiee = True
                appel.save(update_fields=['liste_interview_publiee'])
            self.stdout.write(self.style.SUCCESS("  Liste interview PUBLIÉE (page publique)."))
        else:
            self.stdout.write("\n(Ajoutez --publier pour rendre la liste interview publique.)")

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
