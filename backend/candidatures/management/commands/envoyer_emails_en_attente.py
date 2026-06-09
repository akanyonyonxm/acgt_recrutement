"""Vide la file d'emails en attente, par lots (à appeler via cron).

    python manage.py envoyer_emails_en_attente --limite 90

`--limite` borne le nombre d'envois par exécution pour rester sous la limite
quotidienne de Resend. Lancer plusieurs fois par jour via cron lisse les envois
en masse (publication des retenus).
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from candidatures.models import EmailQueue
from candidatures.services.email import EmailError, envoyer_email


class Command(BaseCommand):
    help = "Envoie les emails en attente dans la file, par lots."

    def add_arguments(self, parser):
        parser.add_argument('--limite', type=int, default=90,
                            help='Nombre max d\'emails envoyés sur cette exécution.')

    def handle(self, *args, **options):
        lot = (
            EmailQueue.objects
            .filter(statut=EmailQueue.Statut.EN_ATTENTE)
            .order_by('cree_le')[:options['limite']]
        )
        envoyes = echecs = 0
        for email in lot:
            try:
                envoyer_email(
                    destinataire=email.destinataire,
                    sujet=email.sujet,
                    template=email.template,
                    contexte=email.contexte,
                )
            except EmailError:
                email.tentatives += 1
                if email.tentatives >= EmailQueue.MAX_TENTATIVES:
                    email.statut = EmailQueue.Statut.ECHEC
                email.save(update_fields=['tentatives', 'statut'])
                echecs += 1
                continue
            email.statut = EmailQueue.Statut.ENVOYE
            email.envoye_le = timezone.now()
            email.save(update_fields=['statut', 'envoye_le'])
            envoyes += 1

        restants = EmailQueue.objects.filter(
            statut=EmailQueue.Statut.EN_ATTENTE,
        ).count()
        self.stdout.write(self.style.SUCCESS(
            f'{envoyes} envoyé(s), {echecs} échec(s), {restants} encore en attente.'
        ))
