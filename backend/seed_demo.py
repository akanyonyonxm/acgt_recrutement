"""Jeu de données de démonstration + compte admin. Idempotent (recrée à neuf).

    venv/Scripts/python.exe seed_demo.py
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.base import ContentFile
from django.core.management import call_command
from candidatures.models import (AppelCandidature, Dossier, TypePiece, PieceExigee,
                                 ListeEligibilite, PieceJointe)
from candidatures.roles import GROUPE_ADMIN, GROUPE_EVALUATEUR
U = get_user_model()

# Repart à neuf sur les données de démo
Dossier.objects.all().delete()
AppelCandidature.objects.filter(titre__startswith='Recrutement').delete()
ListeEligibilite.objects.all().delete()
U.objects.filter(email__in=['admin@acgt.cd', 'evaluateur@acgt.cd', 'candidat@acgt.cd']).delete()

gA = Group.objects.get_or_create(name=GROUPE_ADMIN)[0]
gE = Group.objects.get_or_create(name=GROUPE_EVALUATEUR)[0]

admin = U.objects.create_user(email='admin@acgt.cd', password='Admin2026!',
                              first_name='Admin', email_verifie=True, is_staff=True)
admin.groups.add(gA)
evalu = U.objects.create_user(email='evaluateur@acgt.cd', password='Eval2026!',
                              first_name='Joseph', last_name='Évaluateur', email_verifie=True)
evalu.groups.add(gE)
cand = U.objects.create_user(email='candidat@acgt.cd', password='Cand2026!',
                             first_name='Marie', email_verifie=True)

call_command('init_types_piece')
identite = TypePiece.objects.get(code='identite')
cv = TypePiece.objects.get(code='cv')
diplome = TypePiece.objects.get(code='diplome')

aac = AppelCandidature.objects.create(titre='Recrutement Agents 2026', statut='publie',
                                      description='Appel de démonstration.',
                                      candidature_unique=True)
PieceExigee.objects.create(appel=aac, type_piece=cv, obligatoire=True, ordre=0)
PieceExigee.objects.create(appel=aac, type_piece=identite, obligatoire=True, ordre=1)
PieceExigee.objects.create(appel=aac, type_piece=diplome, obligatoire=True, multiple=True, ordre=2)

for nom, postnom, prenom in [('KABAMBA', 'Tshimanga', 'Jean'),
                             ('MUKENDI', 'Kalala', 'Paul'),
                             ('NSIMBA', 'Mavinga', 'Marie')]:
    ListeEligibilite.objects.create(nom=nom, postnom=postnom, prenom=prenom,
                                    type_eligibilite='stage', annee=2023,
                                    reference=f'STG-{nom[:3]}', est_publie=True)

# Deux dossiers déposés (en attente de validation)
for nom, postnom, prenom in [('Kabamba', 'Tshimanga', 'Jean'), ('Mukendi', 'Kalala', 'Paul')]:
    d = Dossier.objects.create(appel=aac, deposant=cand, nom=nom, postnom=postnom,
                               prenom=prenom, email='candidat@acgt.cd')
    for tp in (identite, cv):
        PieceJointe.objects.create(dossier=d, type_piece=tp,
                                   fichier=ContentFile(b'%PDF-1.4 demo', name=f'{tp.code}.pdf'),
                                   nom_original=f'{tp.code}.pdf', taille=12)
    d.changer_statut(Dossier.Statut.DEPOSE, par=cand, motif='Soumission (démo)')

print("Démo prête.")
print("  Admin       : admin@acgt.cd / Admin2026!")
print("  Évaluateur  : evaluateur@acgt.cd / Eval2026!")
print(f"  {Dossier.objects.count()} dossiers déposés, {ListeEligibilite.objects.count()} éligibles.")
