"""Crée le compte administrateur (superuser) à partir du fichier .env.

Lit ADMIN_EMAIL et ADMIN_PASSWORD. Appelée à chaque démarrage du backend
(entrypoint.sh), donc idempotente :

  - variables absentes        -> ne fait rien (ex. en dev) ;
  - compte inexistant         -> le crée en superuser (email vérifié) ;
  - compte déjà présent       -> garantit seulement ses droits, SANS réécraser
                                 le mot de passe (à changer ensuite via l'admin
                                 Django ou `manage.py changepassword`).

Pour (ré)initialiser le mot de passe d'un compte existant depuis .env, définir
ADMIN_RESET_PASSWORD=True.
"""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Crée/complète le compte admin depuis ADMIN_EMAIL/ADMIN_PASSWORD (.env)."

    def handle(self, *args, **options):
        email = (os.getenv('ADMIN_EMAIL') or '').strip()
        password = os.getenv('ADMIN_PASSWORD') or ''
        reset = (os.getenv('ADMIN_RESET_PASSWORD') or '').lower() in ('1', 'true', 'oui')

        User = get_user_model()

        if not email or not password:
            self.stdout.write(
                'ADMIN_EMAIL/ADMIN_PASSWORD non définis — compte admin non configuré.'
            )
            return

        email = User.objects.normalize_email(email)
        user = User.objects.filter(email__iexact=email).first()

        if user is None:
            User.objects.create_superuser(email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f'Compte admin créé : {email}'))
            return

        # Déjà présent : on garantit les droits (et le mot de passe si demandé).
        modifie = False
        for champ in ('is_superuser', 'is_staff', 'email_verifie'):
            if not getattr(user, champ):
                setattr(user, champ, True)
                modifie = True
        if reset:
            user.set_password(password)
            modifie = True

        if modifie:
            user.save()
            suffixe = ' (mot de passe réinitialisé)' if reset else ' (droits)'
            self.stdout.write(self.style.SUCCESS(f'Compte admin mis à jour{suffixe} : {email}'))
        else:
            self.stdout.write(f'Compte admin déjà configuré : {email}')
