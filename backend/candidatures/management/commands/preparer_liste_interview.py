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

# Les 112 admis à l'interview, DANS L'ORDRE DU FICHIER (nom, postnom, prénom).
INTERVIEW = [
    ("KOUTCHA", "ZACHARIE", "Benjamin"), ("NGANDU", "KANGOMBA", "Patrick"),
    ("KASONGA", "KATALA", "Arsel"), ("PHEBE", "MAKUNGA", "CHRIS"),
    ("DIASOTUKA", "WEFU", "CHADRACK"), ("NYENGELE", "NGINDU", "Rachel"),
    ("SIKI", "GBIAMAGBEDE", "Erick"), ("TSHIBAND", "KASHAL", "JUNIOR"),
    ("Kambere", "Otshudi", "Donel"), ("LISSA", "TEMO", "LUC"),
    ("SIMON", "SWEDI", "Trésor"), ("AKSANTI", "BALOLA", "Jackson"),
    ("MABANZA", "MATABISI", "Merci"), ("TUMWAKA", "WATU", "Elie"),
    ("KALONJI", "KALONJI", "Lucien"), ("Landu", "Luyeye", "Romuald"),
    ("MBOMBO", "MUKENDI", "JEREMIE"), ("KOBALEMO", "GBOMA", "Horizon"),
    ("Mayele", "Lemba", "Dieuleveut"), ("Mpombo", "Bakonga", "Fiston"),
    ("KUYIBUKA", "YAAV", "SAMUEL"), ("Mutombo", "Kabeya", "EPHREM junior"),
    ("KANDA", "KALONJI", "Dorea"), ("MWESHI", "KYALONDAWA", "JONATHAN"),
    ("KUMPI", "LUZINGU", "LE GERME"), ("NZINGA", "NDOSA", "Issac"),
    ("BASILUA", "MBOMBI", "GLODI"), ("KIMONA", "MUKOLO", "JOHN"),
    ("ODIA", "ILUNGA", "Dorcas"), ("Simba", "Mukanjila", "Julien"),
    ("BUKASA", "MUNYOKA", "BERTRAND"), ("METRE", "CONSTANTIN", "BERLYSSE"),
    ("CILUMBU", "CINGUTA", "SHEKINA"), ("Bya’ene", "Akulu", "Jason"),
    ("KAKULE", "ESPERANT", "JOSUE"), ("Maluma", "Kapesa", "Christ"),
    ("BULUMUKA", "NTENSER", "Sabin"), ("MUKUNA", "KATAKU", "PRINCESSE"),
    ("Sabihene", "Masengo", "Gloria"), ("KABWANGALA", "KHABA", "NESTORINE"),
    ("KIALU", "KALONJI", "John"), ("LUBEMBA", "FUAMBA", "Jures"),
    ("TAMBWE", "MUTUNGU", "--"), ("KANGUDIA", "MBUYI", "Patient"),
    ("KUKAMBISA", "SONIKA", "Parfait"), ("Landu", "Bulendolo", "Silver"),
    ("Likeke", "Mbela", "Emmanuel"), ("MUKENDI", "TSHIPETA", "Gedeon"),
    ("CHIKURU", "CENTWALI", "Fidele"), ("METRE", "AMANI", "Daniel"),
    ("PHAMBU", "PFUTI", "Abel"), ("Kamanga", "Mbuyi", "Eric"),
    ("SOPI", "LUEMBA", "Nathan"), ("KOLOKOTA", "NDONGOMBE", "Merdi"),
    ("Mabibi", "Ngedi", "George"), ("Mpova", "Magua", "Exauce"),
    ("EBENGO", "WOKIKI", "Christian"), ("KIANGANA", "MAYEMBA", "GILVANY"),
    ("BITODI", "LEYA", "Jonathan"), ("NLEMVO", "MALUNDAMA", "NOE"),
    ("TSASA", "TSASA", "Kenedy"), ("MBUKULU", "TUVELELA", "Louange"),
    ("YAMBENGA", "KILONDO", "Yams"), ("ABELI", "KYENENGWA", "LEON"),
    ("KASONGA", "NEDI", "MICHEL"), ("KONGOL", "A MUKENG", "Caleb"),
    ("Labu", "Mabanga", "Elie"), ("Tshivuadi", "Mutanda", "Thomas"),
    ("BASHONGA", "SHEMA", "KETSIA"), ("KARNIB", "DINZEY", "BOVARY"),
    ("LUKUSA", "CYUNZA", "JEAN ESTIME"), ("Meya", "Ndamba", "Hervé"),
    ("WEMBOLENGA", "OMALOKENGE", "MICHAËL"), ("YODI", "DJELA", "MAYS"),
    ("SUMBA", "MALY", "BOAZ"), ("KABENA", "MUTAMBA", "SCHADRACK"),
    ("Lembalemba", "Katawa", "Willy"), ("MATONA", "MATONA", "JONATHAN"),
    ("LONGA", "BUAKI", "Benjamin"), ("Zenga", "Makengele", "Joel"),
    ("TUNDULA", "PENE-DIKONDO", "SIMON"), ("MATONDO", "NDAYA", "Rey"),
    ("LUMBALA", "KAPETA", "Aaron"), ("MALUDAMA", "PEDRO", "GRACE"),
    ("TASA", "OTSHUDIEMA", "Einstein"), ("Kalala", "Tshitenge", "Grace"),
    ("KALUNDA", "", "Ludovic"), ("Mutombo", "Kabisa", "Chancellevie"),
    ("ISSA", "ELECA", "Nathan"), ("KIMBUMBA", "OTE-A-YIM", "Gracia"),
    ("Mbom", "Mbaka", "Georges"), ("IPALA", "TAA’MBAK", "Richard"),
    ("BAKABIKA", "BIYELA", "AUDRY"), ("Mwaiyanga", "Ngbanga", "Maurice"),
    ("Kabwe", "Biseba", "Evardy"), ("Kayumba", "Kalonji", "Elie"),
    ("KIBUSU", "NKALE", "Glody"), ("MIAFUKAMA", "DIZA", "EMMANUEL GRACE"),
    ("MBUDI", "TSHINGANA", "JOHN"), ("Ibalansimi", "Ekenge", "Marien"),
    ("Bonkoy", "Longonda", "isaac"), ("YIMBA", "BAYIKIDI", "Graddy"),
    ("Tulu", "Tulu", "Norman"), ("Mbuba", "Shongo", "Michee"),
    ("NDOSIMAU", "LUKAU", "Christian"), ("MUSHAGASHA", "MUNGANGA", "Jackson"),
    ("Kawende", "Mioma", "Aston"), ("LUMBALA", "MBUYI", "JOSUE"),
    ("AKONKWA", "KAVUHA", "Bertin"), ("NTUMBA", "CIALA", "AARON"),
    ("MAMBA", "KALAMBA", "Jean"), ("Mweze", "Ngoy", "Daniel"),
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

        if not dry:
            appel.retenus_definitifs.update(admis_interview=False, interview_ordre=0)
        marques, introuvables, a_maj, ordre = 0, [], [], 0
        for nom, postnom, prenom in INTERVIEW:
            cle = normaliser_texte(f'{nom} {postnom} {prenom}')
            entrees = par_nom.get(cle)
            if not entrees:
                introuvables.append((nom, postnom, prenom))
                continue
            ordre += 1
            for e in entrees:
                e.admis_interview = True
                e.interview_ordre = ordre
                a_maj.append(e)
            marques += 1
        if not dry:
            RetenuDefinitif.objects.bulk_update(a_maj, ['admis_interview', 'interview_ordre'])

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
