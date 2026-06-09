"""Comptes utilisateurs ACGT.

L'identifiant de connexion est l'**email** (pas un nom d'utilisateur). Trois
profils cohabitent dans la même table :

  - Candidats : auto-inscrits, hors groupes staff. Doivent vérifier leur email.
  - Administrateurs / Évaluateurs : créés en back-office, placés dans les
    groupes correspondants (voir candidatures.roles).

Un proche peut déposer un dossier au nom d'un tiers : le compte (déposant) n'est
donc pas forcément la personne nommée dans le dossier. Voir Dossier.deposant.
"""

import uuid

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Manager utilisant l'email comme identifiant (au lieu du username)."""

    use_in_migrations = True

    def _creer(self, email, password, **extra):
        if not email:
            raise ValueError("L'adresse email est obligatoire.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault('is_staff', False)
        extra.setdefault('is_superuser', False)
        return self._creer(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        extra.setdefault('email_verifie', True)
        if extra.get('is_staff') is not True:
            raise ValueError("Un superuser doit avoir is_staff=True.")
        if extra.get('is_superuser') is not True:
            raise ValueError("Un superuser doit avoir is_superuser=True.")
        return self._creer(email, password, **extra)


class User(AbstractUser):
    """Utilisateur identifié par email."""

    # On neutralise le username hérité : l'email est l'identifiant.
    username = None
    email = models.EmailField('adresse email', unique=True)

    # Tant que l'email n'est pas vérifié, le candidat ne peut pas déposer.
    email_verifie = models.BooleanField('email vérifié', default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # email + password demandés d'office

    objects = UserManager()

    class Meta:
        verbose_name = 'utilisateur'
        verbose_name_plural = 'utilisateurs'

    def __str__(self):
        return self.email


class JetonEmail(models.Model):
    """Jeton à usage unique envoyé par email (vérification ou reset mot de passe).

    Stateful volontairement : on peut révoquer/expirer un jeton, et tracer son
    utilisation. Un seul jeton actif par (utilisateur, usage) à la fois.
    """

    class Usage(models.TextChoices):
        VERIFICATION = 'verification', 'Vérification email'
        REINITIALISATION = 'reinitialisation', 'Réinitialisation mot de passe'

    DUREE_VALIDITE = timezone.timedelta(hours=48)

    jeton = models.UUIDField('jeton', default=uuid.uuid4, unique=True, editable=False)
    utilisateur = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='jetons',
        verbose_name='utilisateur',
    )
    usage = models.CharField('usage', max_length=20, choices=Usage.choices)
    cree_le = models.DateTimeField('créé le', auto_now_add=True)
    expire_le = models.DateTimeField('expire le')
    utilise_le = models.DateTimeField('utilisé le', null=True, blank=True)

    class Meta:
        verbose_name = 'jeton email'
        verbose_name_plural = 'jetons email'
        ordering = ['-cree_le']

    def save(self, *args, **kwargs):
        if not self.expire_le:
            self.expire_le = timezone.now() + self.DUREE_VALIDITE
        super().save(*args, **kwargs)

    @property
    def est_valide(self):
        return self.utilise_le is None and timezone.now() < self.expire_le

    def consommer(self):
        """Marque le jeton comme utilisé (à appeler après action réussie)."""
        self.utilise_le = timezone.now()
        self.save(update_fields=['utilise_le'])

    @classmethod
    def emettre(cls, utilisateur, usage):
        """Crée un nouveau jeton et invalide les anciens du même usage."""
        cls.objects.filter(
            utilisateur=utilisateur, usage=usage, utilise_le__isnull=True,
        ).update(utilise_le=timezone.now())
        return cls.objects.create(utilisateur=utilisateur, usage=usage)

    def __str__(self):
        return f'{self.get_usage_display()} — {self.utilisateur.email}'
