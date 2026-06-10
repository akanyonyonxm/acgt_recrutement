"""Génère 500 personnes éligibles publiées (noms RDC réalistes).

    venv/Scripts/python.exe seed_eligibles.py
"""
import os
import random
import string
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from candidatures.models import ListeEligibilite
from candidatures.utils import normaliser_texte

random.seed(2026)  # reproductible

# Génère des codes publics uniques de 4 caractères (lettres majuscules + chiffres).
_ALPHABET = string.ascii_uppercase + string.digits
_codes = set()


def generer_code():
    while True:
        c = ''.join(random.choice(_ALPHABET) for _ in range(4))
        if c not in _codes:
            _codes.add(c)
            return c

NOMS = [
    'KABAMBA', 'MUKENDI', 'NSIMBA', 'TSHILOMBO', 'ILUNGA', 'MWAMBA', 'KALALA',
    'MBUYI', 'KASONGO', 'LUKUSA', 'NGALULA', 'TSHIMANGA', 'MUTOMBO', 'KABONGO',
    'BANZA', 'NGOYI', 'KAZADI', 'MUKEBA', 'LUMBU', 'MAVINGA', 'NKANGA',
    'LUTUMBA', 'MABELE', 'KIBWE', 'BWANGA', 'MULUMBA', 'KAYEMBE', 'NTUMBA',
    'BADIBANGA', 'KAPINGA', 'MBALA', 'LUNDA', 'MAKIESE', 'NZUZI', 'DIATEZUA',
    'KIESE', 'LUYEYE', 'MASUDI', 'BAHATI', 'AMISI', 'SELEMANI', 'RAMAZANI',
    'BYAMUNGU', 'CIZUNGU', 'BASHIGE', 'MUSHAGALUSA', 'BALAGIZI', 'KASEREKA',
    'KAMBALE', 'PALUKU',
]
POSTNOMS = [
    'Tshimanga', 'Kalala', 'Mavinga', 'Ilunga', 'Mbuyi', 'Kabuya', 'Mwepu',
    'Nzeza', 'Lukoki', 'Mbenza', 'Kanku', 'Tshibangu', 'Wa Mukendi', 'Beya',
    'Kasongo', 'Mpoyi', 'Ntambwe', 'Lufuluabo', 'Mukuna', 'Kazembe',
    'Bukasa', 'Cibola', 'Disashi', 'Ekanga', 'Falanga',
]
PRENOMS = [
    'Jean', 'Paul', 'Marie', 'Joseph', 'Pierre', 'Patrick', 'Christian',
    'Gloire', 'Grâce', 'Esther', 'Daniel', 'Emmanuel', 'Bénédicte', 'Sylvie',
    'Trésor', 'Divine', 'Merveille', 'Josué', 'Nathan', 'Ruth', 'Sarah',
    'David', 'Samuel', 'Aimée', 'Chance', 'Dieudonné', 'Espoir', 'Junior',
    'Plamedi', 'Nadège', 'Olivier', 'Carine', 'Fabrice', 'Gauthier',
    'Henriette', 'Isaac', 'Jonathan', 'Keren', 'Laetitia', 'Moïse',
]

ListeEligibilite.objects.all().delete()

objets = []
for i in range(500):
    nom = random.choice(NOMS)
    postnom = random.choice(POSTNOMS)
    prenom = random.choice(PRENOMS)
    type_e = random.choice(['stage', 'candidature'])
    annee = random.randint(2020, 2025)
    prefixe = 'STG' if type_e == 'stage' else 'CAND'
    objets.append(ListeEligibilite(
        nom=nom, postnom=postnom, prenom=prenom,
        code=generer_code(),
        type_eligibilite=type_e, annee=annee,
        reference=f'{prefixe}-{annee}-{i + 1:04d}',
        est_publie=True,
        texte_recherche=normaliser_texte(f'{nom} {postnom} {prenom}'),
    ))

ListeEligibilite.objects.bulk_create(objets, batch_size=500)
print(f'{ListeEligibilite.objects.count()} personnes éligibles publiées.')
