"""Modèles métier du traitement des dossiers d'appel à candidature ACGT.

Étape 1 : le cœur du système = le cycle de vie (statuts) d'un dossier.

Workflow figé :

    DÉPOSÉ ──(admin: approuver)──► EN_EXAMEN ──(évaluateur)──┬─► RETENU
       │                                                    └─► NON_RETENU
       └──(admin: rejeter)──► REJETÉ

RETENU / NON_RETENU / REJETÉ sont des états terminaux.
"""

import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone

# Pièces jointes : types de fichiers et taille acceptés.
EXTENSIONS_AUTORISEES = ['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx']
TAILLE_MAX_PIECE = 5 * 1024 * 1024  # 5 Mo


def chemin_piece_jointe(instance, nom_fichier):
    """Range chaque pièce sous dossiers/<id>/<uuid>.<ext> (nom non devinable)."""
    ext = Path(nom_fichier).suffix.lower()
    return f'dossiers/{instance.dossier_id}/{uuid.uuid4().hex}{ext}'


def chemin_doc_reclamation(instance, nom_fichier):
    """Range un document de réclamation sous reclamations/<uuid>.<ext> (nom non devinable)."""
    ext = Path(nom_fichier).suffix.lower()
    return f'reclamations/{uuid.uuid4().hex}{ext}'


class AppelCandidature(models.Model):
    """Une campagne de recrutement (AAC)."""

    class Statut(models.TextChoices):
        BROUILLON = 'brouillon', 'Brouillon'
        PUBLIE = 'publie', 'Publié'
        CLOTURE = 'cloture', 'Clôturé'

    titre = models.CharField('titre', max_length=200)
    description = models.TextField('description', blank=True)
    statut = models.CharField(
        'statut', max_length=20,
        choices=Statut.choices, default=Statut.BROUILLON,
    )
    date_ouverture = models.DateField("date d'ouverture", null=True, blank=True)
    date_cloture = models.DateField('date de clôture', null=True, blank=True)
    # Pilote l'affichage public de la liste (PROVISOIRE) des personnes retenues.
    liste_retenus_publiee = models.BooleanField(
        'liste des retenus publiée', default=False,
    )
    # Liste DÉFINITIVE : retenus publiés + recours validés, figée avec un code
    # stable par personne. Quand elle est publiée, elle REMPLACE la provisoire
    # sur la page publique des retenus.
    liste_definitive_publiee = models.BooleanField(
        'liste définitive publiée', default=False,
    )
    # Message spécifique affiché sur la page publique quand la liste DÉFINITIVE
    # est publiée (échéance du test, ville d'examen hors Kinshasa, etc.).
    message_retenus_definitif = models.TextField(
        'message public (liste définitive)', blank=True,
    )
    # Instructions du test affichées aux retenus (bouton « Instructions » sur la
    # page publique de la liste définitive). Vide = texte par défaut côté front.
    instructions_examen = models.TextField(
        'instructions du test (liste définitive)', blank=True,
    )
    # Affiche la salle d'examen sur la page publique (liste définitive + badge).
    afficher_salle_public = models.BooleanField(
        'afficher la salle au public', default=False,
    )
    # Communiqué affiché en haut de la page publique des retenus (échéances de
    # recours, critères, date de la liste définitive…). Vide = aucun bandeau.
    message_retenus = models.TextField(
        'message public (page des retenus)', blank=True,
    )
    # Date/heure limite pour déposer un recours. Passée cette échéance, le dépôt
    # de recours est fermé (bouton masqué, soumission refusée) pour laisser le
    # comité traiter. Vide = pas d'échéance (recours ouvert tant que publié).
    date_limite_recours = models.DateTimeField(
        'date limite des recours', null=True, blank=True,
    )
    # Si True, un même compte ne peut déposer qu'un seul dossier pour cet appel.
    candidature_unique = models.BooleanField(
        'candidature unique par compte', default=False,
    )

    cree_le = models.DateTimeField('créé le', auto_now_add=True)
    modifie_le = models.DateTimeField('modifié le', auto_now=True)

    class Meta:
        verbose_name = 'appel à candidature'
        verbose_name_plural = 'appels à candidature'
        ordering = ['-cree_le']

    def __str__(self):
        return self.titre

    @staticmethod
    def recours_ouverts():
        """Le dépôt de recours est-il ouvert (au moins un appel publié dont
        l'échéance n'est pas passée — ou sans échéance) ? Sinon, recours clôturés."""
        appels = AppelCandidature.objects.filter(liste_retenus_publiee=True)
        if not appels.exists():
            return False
        maintenant = timezone.now()
        return any(
            a.date_limite_recours is None or a.date_limite_recours > maintenant
            for a in appels
        )

    @property
    def est_ouvert(self):
        """Les candidatures sont-elles ouvertes pour cet appel ?

        Source de vérité unique pour autoriser le dépôt/la soumission : un appel
        n'accepte des dossiers que s'il est PUBLIÉ. « Clôturé » (ou « Brouillon »)
        ferme la candidature (bouton « Postuler » masqué, dépôt refusé côté
        serveur)."""
        return self.statut == self.Statut.PUBLIE


class Dossier(models.Model):
    """Un dossier de candidature déposé sur la plateforme.

    Le dossier est autonome : le déposant saisit librement nom/postnom/prénom
    (qui ne correspondent pas forcément à l'orthographe de la liste ACGT) et un
    email de contact (qui peut être celui d'un proche). Le rattachement à la
    liste d'éligibilité est fait, si besoin, par l'admin lors de la validation.
    """

    class Statut(models.TextChoices):
        BROUILLON = 'brouillon', 'Brouillon'
        DEPOSE = 'depose', 'Déposé'
        EN_EXAMEN = 'en_examen', 'En examen'
        RETENU = 'retenu', 'Retenu'
        NON_RETENU = 'non_retenu', 'Non retenu'
        REJETE = 'rejete', 'Rejeté'

    # Transitions autorisées : statut courant -> statuts atteignables.
    #   BROUILLON : le candidat construit son dossier (ajout/retrait de pièces).
    #   La soumission (BROUILLON -> DÉPOSÉ) verrouille le dossier.
    TRANSITIONS = {
        Statut.BROUILLON: {Statut.DEPOSE},
        Statut.DEPOSE: {Statut.EN_EXAMEN, Statut.REJETE},
        # L'étape « examen » n'est plus utilisée dans le traitement courant
        # (validation directe DÉPOSÉ → RETENU). On garde EN_EXAMEN dans la
        # machine à états (les dossiers le traversent), et on autorise le rejet
        # depuis cet état pour pouvoir traiter ceux qui y séjournent encore.
        Statut.EN_EXAMEN: {Statut.RETENU, Statut.NON_RETENU, Statut.REJETE},
        Statut.RETENU: set(),
        Statut.NON_RETENU: set(),
        Statut.REJETE: set(),
    }

    STATUTS_TERMINAUX = {Statut.RETENU, Statut.NON_RETENU, Statut.REJETE}

    appel = models.ForeignKey(
        AppelCandidature,
        on_delete=models.PROTECT,
        related_name='dossiers',
        verbose_name='appel à candidature',
    )
    # Poste/fonction visé(e) par la candidature (Architecte, Ingénieur civil…).
    poste = models.ForeignKey(
        'Poste',
        on_delete=models.PROTECT,
        related_name='dossiers',
        null=True, blank=True,
        verbose_name='poste visé',
    )
    # Compte qui a déposé le dossier. Peut différer de la personne nommée
    # ci-dessous (un proche peut postuler à la place de quelqu'un).
    deposant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='dossiers',
        null=True, blank=True,
        verbose_name='déposant',
    )

    # Agent chargé de traiter ce dossier (répartition de la charge entre
    # validateurs). L'affectation suit le dossier sur tout son cycle
    # (approuver → retenir/non-retenir) : c'est le même agent qui le mène à
    # terme. Un admin peut toujours trancher (et réaffecter) ; un validateur
    # seulement les dossiers qui lui sont affectés.
    affecte_a = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='dossiers_affectes',
        verbose_name='affecté à',
        db_index=True,
    )

    # Code du dossier = code public de la liste d'éligibilité (4 caractères).
    # Récupéré au clic sur « Postuler » depuis la liste, ou saisi à la main.
    code = models.CharField('code du dossier', max_length=50, blank=True, db_index=True)

    # Identité saisie librement par le déposant.
    nom = models.CharField('nom', max_length=100)
    postnom = models.CharField('postnom', max_length=100, blank=True)
    prenom = models.CharField('prénom', max_length=100)
    email = models.EmailField('email de contact')

    # Ligne de la liste d'éligibilité que l'admin a reconnue lors de la
    # validation (traçabilité : « ce dossier vise telle personne »). Optionnel.
    ligne_eligibilite = models.ForeignKey(
        'ListeEligibilite',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='dossiers',
        verbose_name='ligne d\'éligibilité',
    )

    statut = models.CharField(
        'statut', max_length=20,
        choices=Statut.choices, default=Statut.BROUILLON,
        db_index=True,
    )

    # Forme normalisée de « nom postnom prénom » pour la recherche tolérante
    # (notamment la liste publique des retenus). Calculée à l'enregistrement.
    texte_recherche = models.CharField(
        'texte de recherche', max_length=320, editable=False, db_index=True,
        default='',
    )

    cree_le = models.DateTimeField('déposé le', auto_now_add=True)
    modifie_le = models.DateTimeField('modifié le', auto_now=True)

    class Meta:
        verbose_name = 'dossier'
        verbose_name_plural = 'dossiers'
        ordering = ['-cree_le']

    def save(self, *args, **kwargs):
        from .utils import normaliser_texte
        self.texte_recherche = normaliser_texte(
            f'{self.nom} {self.postnom} {self.prenom}'
        )
        super().save(*args, **kwargs)

    def __str__(self):
        return f'#{self.pk} — {self.nom} {self.postnom} {self.prenom}'.strip()

    @property
    def est_terminal(self):
        return self.statut in self.STATUTS_TERMINAUX

    @property
    def modifiable(self):
        """Le dossier n'est éditable (pièces, identité) qu'en brouillon."""
        return self.statut == self.Statut.BROUILLON

    def pieces_obligatoires_manquantes(self):
        """Types de pièce obligatoires de l'AAC non encore fournis."""
        fournis = set(self.pieces.values_list('type_piece_id', flat=True))
        return [
            pe.type_piece
            for pe in self.appel.pieces_exigees.filter(obligatoire=True)
                              .select_related('type_piece')
            if pe.type_piece_id not in fournis
        ]

    @property
    def est_complet(self):
        return not self.pieces_obligatoires_manquantes()

    def ligne_eligibilite_correspondante(self):
        """LA ligne de la liste d'éligibilité qui désigne cette même personne.

        Critère STRICT : le nom complet (nom **et** postnom **et** prénom) est
        identique. La comparaison se fait sur `texte_recherche` (forme
        normalisée : sans accents, minuscules, espaces simples), donc insensible
        aux accents et à la casse, et un champ vide des deux côtés est bien
        considéré comme identique. Jamais le code (des candidats saisissent le
        code d'autrui). Renvoie la ligne seulement si elle est unique (si la
        liste contient deux personnes du même nom complet → None, l'admin
        tranche).
        """
        if not self.texte_recherche:
            return None
        lignes = list(
            ListeEligibilite.objects.filter(texte_recherche=self.texte_recherche)[:2]
        )
        if len(lignes) == 1:
            return lignes[0]
        return None

    def transitions_possibles(self):
        """Statuts atteignables depuis l'état courant."""
        return self.TRANSITIONS.get(self.statut, set())

    def peut_passer_a(self, nouveau_statut):
        return nouveau_statut in self.transitions_possibles()

    def changer_statut(self, nouveau_statut, par=None, motif=''):
        """Change le statut en validant la transition et en journalisant.

        Lève ValidationError si la transition n'est pas autorisée. Trace le
        changement dans HistoriqueStatut (audit : qui, quand, quoi, pourquoi).
        """
        if nouveau_statut == self.statut:
            raise ValidationError("Le dossier est déjà dans ce statut.")
        if not self.peut_passer_a(nouveau_statut):
            libelle = self.Statut(self.statut).label
            cible = self.Statut(nouveau_statut).label
            raise ValidationError(
                f"Transition interdite : un dossier « {libelle} » ne peut pas "
                f"passer à « {cible} »."
            )

        ancien = self.statut
        self.statut = nouveau_statut
        self.save(update_fields=['statut', 'modifie_le'])

        HistoriqueStatut.objects.create(
            dossier=self,
            ancien_statut=ancien,
            nouveau_statut=nouveau_statut,
            par=par,
            motif=motif,
        )
        return self


class HistoriqueStatut(models.Model):
    """Journal d'audit des changements de statut (traçabilité RGPD)."""

    dossier = models.ForeignKey(
        Dossier,
        on_delete=models.CASCADE,
        related_name='historique',
        verbose_name='dossier',
    )
    ancien_statut = models.CharField(
        'ancien statut', max_length=20, choices=Dossier.Statut.choices,
    )
    nouveau_statut = models.CharField(
        'nouveau statut', max_length=20, choices=Dossier.Statut.choices,
    )
    par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='effectué par',
    )
    motif = models.TextField('motif', blank=True)
    horodatage = models.DateTimeField('le', default=timezone.now)

    class Meta:
        verbose_name = 'historique de statut'
        verbose_name_plural = 'historique des statuts'
        ordering = ['-horodatage']

    def __str__(self):
        return f'{self.dossier_id} : {self.ancien_statut} → {self.nouveau_statut}'


class PieceJointe(models.Model):
    """Fichier joint à un dossier (CV, identité, attestation…).

    Stocké hors de la racine web (MEDIA_ROOT privé) ; jamais d'URL publique.
    Le téléchargement passe par une vue authentifiée et contrôlée.
    """

    dossier = models.ForeignKey(
        Dossier,
        on_delete=models.CASCADE,
        related_name='pieces',
        verbose_name='dossier',
    )
    type_piece = models.ForeignKey(
        'TypePiece',
        on_delete=models.PROTECT,
        related_name='pieces_jointes',
        verbose_name='type de pièce',
    )
    fichier = models.FileField(
        'fichier',
        upload_to=chemin_piece_jointe,
        validators=[FileExtensionValidator(EXTENSIONS_AUTORISEES)],
    )
    nom_original = models.CharField('nom d\'origine', max_length=255, blank=True)
    taille = models.PositiveIntegerField('taille (octets)', default=0)
    cree_le = models.DateTimeField('déposé le', auto_now_add=True)

    class Meta:
        verbose_name = 'pièce jointe'
        verbose_name_plural = 'pièces jointes'
        ordering = ['type_piece__ordre', 'cree_le']

    def __str__(self):
        return f'{self.type_piece} — dossier #{self.dossier_id}'


class Poste(models.Model):
    """Référentiel des postes/fonctions visés (Architecte, Ingénieur civil…).

    Géré dans Django Admin ; proposé en liste déroulante au candidat lorsqu'il
    dépose son dossier.
    """

    libelle = models.CharField('intitulé', max_length=120, unique=True)
    description = models.CharField('description', max_length=255, blank=True)
    actif = models.BooleanField('actif', default=True)
    ordre = models.PositiveIntegerField("ordre d'affichage", default=0)

    class Meta:
        verbose_name = 'poste'
        verbose_name_plural = 'postes'
        ordering = ['ordre', 'libelle']

    def __str__(self):
        return self.libelle


class TypePiece(models.Model):
    """Référentiel des types de pièces (Identité, CV, Lettre de motivation…).

    Géré dans Django Admin. Sert de liste déroulante côté candidat (à quoi
    correspond chaque fichier déposé) et de base aux pièces exigées par AAC.
    """

    code = models.SlugField('code', max_length=50, unique=True)
    libelle = models.CharField('libellé', max_length=100)
    description = models.CharField('description', max_length=255, blank=True)
    actif = models.BooleanField('actif', default=True)
    ordre = models.PositiveIntegerField('ordre d\'affichage', default=0)

    class Meta:
        verbose_name = 'type de pièce'
        verbose_name_plural = 'types de pièce'
        ordering = ['ordre', 'libelle']

    def __str__(self):
        return self.libelle


class PieceExigee(models.Model):
    """Pièce attendue pour un appel à candidature donné.

    Pilote la checklist du dépôt candidat : un dossier ne peut être envoyé que
    si toutes les pièces `obligatoire=True` de son AAC sont fournies (Lot 4).
    """

    appel = models.ForeignKey(
        AppelCandidature,
        on_delete=models.CASCADE,
        related_name='pieces_exigees',
        verbose_name='appel à candidature',
    )
    type_piece = models.ForeignKey(
        TypePiece,
        on_delete=models.PROTECT,
        related_name='exigences',
        verbose_name='type de pièce',
    )
    obligatoire = models.BooleanField('obligatoire', default=True)
    multiple = models.BooleanField('plusieurs fichiers autorisés', default=False)
    ordre = models.PositiveIntegerField('ordre d\'affichage', default=0)

    class Meta:
        verbose_name = 'pièce exigée'
        verbose_name_plural = 'pièces exigées'
        ordering = ['ordre', 'type_piece__libelle']
        constraints = [
            models.UniqueConstraint(
                fields=['appel', 'type_piece'],
                name='unique_piece_exigee_par_appel',
            ),
        ]

    def __str__(self):
        marque = '' if self.obligatoire else ' (optionnelle)'
        return f'{self.appel} — {self.type_piece}{marque}'


class ListeEligibilite(models.Model):
    """Personne autorisée à postuler (ancien stagiaire ou ancien candidat).

    Importée depuis Excel par l'ACGT. Sert à deux usages distincts :
      - affichage public (lecture seule) : NOM · POSTNOM · PRÉNOM uniquement,
        des personnes dont `est_publie=True` ;
      - outil de recherche tolérante pour l'admin lors de la validation.

    La `reference` interne n'est jamais exposée publiquement.
    """

    class Type(models.TextChoices):
        STAGE = 'stage', 'Stage'
        CANDIDATURE = 'candidature', 'Ancienne candidature'

    nom = models.CharField('nom', max_length=100)
    postnom = models.CharField('postnom', max_length=100, blank=True)
    prenom = models.CharField('prénom', max_length=100, blank=True)
    type_eligibilite = models.CharField(
        'type', max_length=20, choices=Type.choices, default=Type.STAGE,
        blank=True,
    )
    annee = models.PositiveIntegerField('année', null=True, blank=True)
    # Code/numéro public de la personne (importé du fichier, affiché sur la liste).
    code = models.CharField('code', max_length=50, blank=True, db_index=True)
    reference = models.CharField('référence interne', max_length=100, blank=True)

    # Forme normalisée (sans accents, minuscules) de « nom postnom prénom »,
    # calculée à l'enregistrement. Pilote la recherche tolérante.
    texte_recherche = models.CharField(
        'texte de recherche', max_length=320, editable=False, db_index=True,
        default='',
    )
    est_publie = models.BooleanField('publié', default=False, db_index=True)

    cree_le = models.DateTimeField('créé le', auto_now_add=True)
    modifie_le = models.DateTimeField('modifié le', auto_now=True)

    class Meta:
        verbose_name = 'personne éligible'
        verbose_name_plural = 'liste d\'éligibilité'
        ordering = ['nom', 'postnom', 'prenom']

    def save(self, *args, **kwargs):
        from .utils import normaliser_texte
        self.texte_recherche = normaliser_texte(
            f'{self.nom} {self.postnom} {self.prenom}'
        )
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.nom} {self.postnom} {self.prenom}'.strip()


class AffectationEvaluateur(models.Model):
    """Désignation d'un évaluateur sur un dossier.

    Être désigné donne l'**accès en consultation** au dossier. Seuls les
    évaluateurs désignés avec `peut_valider=True` peuvent changer le statut
    (retenir / non-retenir). C'est la règle « tous les désignés accèdent, les
    autorisés valident ».
    """

    dossier = models.ForeignKey(
        Dossier,
        on_delete=models.CASCADE,
        related_name='affectations',
        verbose_name='dossier',
    )
    evaluateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='affectations',
        verbose_name='évaluateur',
    )
    peut_valider = models.BooleanField('autorisé à valider', default=False)
    cree_le = models.DateTimeField('désigné le', auto_now_add=True)

    class Meta:
        verbose_name = 'affectation d\'évaluateur'
        verbose_name_plural = 'affectations d\'évaluateur'
        constraints = [
            models.UniqueConstraint(
                fields=['dossier', 'evaluateur'],
                name='unique_affectation_par_dossier',
            ),
        ]

    def __str__(self):
        marque = ' (validateur)' if self.peut_valider else ''
        return f'{self.evaluateur} → dossier #{self.dossier_id}{marque}'


class Evaluation(models.Model):
    """Avis d'un évaluateur sur un dossier (consultatif).

    Pas de note chiffrée pour l'instant : un avis libre + une recommandation.
    Le changement de statut effectif reste l'action retenir/non-retenir, faite
    par un évaluateur autorisé. Un évaluateur a au plus une évaluation par
    dossier (modifiable).
    """

    class Recommandation(models.TextChoices):
        RETENU = 'retenu', 'Retenu'
        NON_RETENU = 'non_retenu', 'Non retenu'
        RESERVE = 'reserve', 'Réservé'

    dossier = models.ForeignKey(
        Dossier,
        on_delete=models.CASCADE,
        related_name='evaluations',
        verbose_name='dossier',
    )
    evaluateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='evaluations',
        verbose_name='évaluateur',
    )
    avis = models.TextField('avis', blank=True)
    recommandation = models.CharField(
        'recommandation', max_length=20,
        choices=Recommandation.choices, default=Recommandation.RESERVE,
    )
    cree_le = models.DateTimeField('créé le', auto_now_add=True)
    modifie_le = models.DateTimeField('modifié le', auto_now=True)

    class Meta:
        verbose_name = 'évaluation'
        verbose_name_plural = 'évaluations'
        ordering = ['-modifie_le']
        constraints = [
            models.UniqueConstraint(
                fields=['dossier', 'evaluateur'],
                name='unique_evaluation_par_evaluateur',
            ),
        ]

    def __str__(self):
        return f'Avis de {self.evaluateur} — dossier #{self.dossier_id}'


class EmailQueue(models.Model):
    """File d'attente d'emails à envoyer en masse (publication des retenus).

    SmarterASP/VPS n'ont pas de worker permanent : les envois en masse sont
    stockés ici puis vidés progressivement par la commande
    `envoyer_emails_en_attente` (cron), pour respecter la limite quotidienne de
    Resend. Les emails transactionnels urgents (accusé, décision individuelle)
    restent envoyés en direct, pas via cette file.
    """

    class Statut(models.TextChoices):
        EN_ATTENTE = 'en_attente', 'En attente'
        ENVOYE = 'envoye', 'Envoyé'
        ECHEC = 'echec', 'Échec'

    MAX_TENTATIVES = 3

    dossier = models.ForeignKey(
        Dossier,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='emails',
        verbose_name='dossier',
    )
    # Campagne d'envoi (ex. résultats d'un appel) : permet de suivre la
    # progression et d'éviter les doublons par destinataire au sein d'un appel.
    appel = models.ForeignKey(
        AppelCandidature, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='emails_queue', verbose_name='appel à candidature',
    )
    categorie = models.CharField('catégorie', max_length=30, blank=True, db_index=True)
    destinataire = models.EmailField('destinataire')
    sujet = models.CharField('sujet', max_length=255)
    template = models.CharField('template', max_length=100)
    contexte = models.JSONField('contexte', default=dict, blank=True)
    statut = models.CharField(
        'statut', max_length=20,
        choices=Statut.choices, default=Statut.EN_ATTENTE, db_index=True,
    )
    tentatives = models.PositiveIntegerField('tentatives', default=0)
    cree_le = models.DateTimeField('créé le', auto_now_add=True)
    envoye_le = models.DateTimeField('envoyé le', null=True, blank=True)

    class Meta:
        verbose_name = 'email en file'
        verbose_name_plural = 'file d\'emails'
        ordering = ['cree_le']

    def __str__(self):
        return f'{self.destinataire} — {self.get_statut_display()}'


class ReclamationEligibilite(models.Model):
    """Réclamation d'une personne absente de la liste d'éligibilité.

    Flux : une personne qui ne trouve pas son nom dépose une réclamation via un
    formulaire public, en joignant l'accusé de réception remis par l'ACGT lors du
    dépôt physique de son dossier. L'admin consulte l'accusé puis VALIDE ou
    REJETTE. À la validation, un `Dossier` est créé et conduit jusqu'à RETENU via
    `Dossier.changer_statut()` (l'invariant de la machine à états est respecté).

    L'accusé est stocké dans MEDIA_ROOT privé (nom UUID) ; jamais d'URL publique.
    """

    class Statut(models.TextChoices):
        EN_ATTENTE = 'en_attente', 'En attente'
        VALIDEE = 'validee', 'Validée'
        REJETEE = 'rejetee', 'Rejetée'

    appel = models.ForeignKey(
        AppelCandidature,
        on_delete=models.PROTECT,
        related_name='reclamations',
        verbose_name='appel à candidature',
    )
    # Poste/fonction visé(e), déclaré par le réclamant : évite à l'admin de le
    # deviner depuis le CV au moment de valider. Nullable : les réclamations
    # antérieures à ce champ n'en ont pas (l'admin choisit alors manuellement).
    poste = models.ForeignKey(
        'Poste',
        on_delete=models.PROTECT,
        related_name='reclamations',
        null=True, blank=True,
        verbose_name='poste souhaité',
    )
    # Identité revendiquée (saisie libre, comme pour un dossier).
    nom = models.CharField('nom', max_length=100)
    postnom = models.CharField('postnom', max_length=100, blank=True)
    prenom = models.CharField('prénom', max_length=100)
    email = models.EmailField('email de contact')
    telephone = models.CharField('téléphone', max_length=40, blank=True)
    message = models.TextField('message', blank=True)

    statut = models.CharField(
        'statut', max_length=20,
        choices=Statut.choices, default=Statut.EN_ATTENTE, db_index=True,
    )
    motif = models.TextField('motif de la décision', blank=True)
    # Agent chargé de traiter cette réclamation (répartition de la charge entre
    # plusieurs validateurs). Affectation = qui DOIT la traiter ; `traite_par` =
    # qui l'a effectivement tranchée. Un admin peut toujours trancher ;
    # un validateur seulement les réclamations qui lui sont affectées.
    affecte_a = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reclamations_affectees',
        verbose_name='affectée à',
        db_index=True,
    )
    traite_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reclamations_traitees',
        verbose_name='traité par',
    )
    traite_le = models.DateTimeField('traité le', null=True, blank=True)
    # Dossier créé à la validation (traçabilité du lien réclamation -> retenu).
    dossier_cree = models.ForeignKey(
        Dossier,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reclamation_origine',
        verbose_name='dossier créé',
    )

    texte_recherche = models.CharField(
        'texte de recherche', max_length=320, editable=False, db_index=True, default='',
    )
    cree_le = models.DateTimeField('reçue le', auto_now_add=True)

    class Meta:
        verbose_name = 'réclamation d\'éligibilité'
        verbose_name_plural = 'réclamations d\'éligibilité'
        ordering = ['-cree_le']

    def save(self, *args, **kwargs):
        from .utils import normaliser_texte
        self.texte_recherche = normaliser_texte(f'{self.nom} {self.postnom} {self.prenom}')
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Réclamation #{self.pk} — {self.nom} {self.prenom} ({self.get_statut_display()})'


class DocumentReclamation(models.Model):
    """Justificatif joint à une réclamation (accusé, CV, identité, diplôme…).

    Stocké dans MEDIA_ROOT privé (nom UUID) ; jamais d'URL publique. Le diplôme
    peut être fourni en plusieurs exemplaires.
    """

    class Type(models.TextChoices):
        ACCUSE = 'accuse', 'Accusé de réception'
        CV = 'cv', 'CV'
        IDENTITE = 'identite', "Pièce d'identité"
        DIPLOME = 'diplome', 'Diplôme'

    reclamation = models.ForeignKey(
        ReclamationEligibilite,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name='réclamation',
    )
    type = models.CharField('type', max_length=20, choices=Type.choices)
    fichier = models.FileField(
        'fichier',
        upload_to=chemin_doc_reclamation,
        validators=[FileExtensionValidator(EXTENSIONS_AUTORISEES)],
    )
    nom_original = models.CharField("nom d'origine", max_length=255, blank=True)
    taille = models.PositiveIntegerField('taille (octets)', default=0)
    cree_le = models.DateTimeField('déposé le', auto_now_add=True)

    class Meta:
        verbose_name = 'document de réclamation'
        verbose_name_plural = 'documents de réclamation'
        ordering = ['type', 'cree_le']

    def __str__(self):
        return f'{self.get_type_display()} — réclamation #{self.reclamation_id}'


class CritereValidation(models.Model):
    """Critère d'une grille de validation, configurable dans la console.

    Sert de checklist manuelle à cocher avant de valider (réclamation et/ou
    dossier). Les libellés peuvent changer ; `actif=False` retire le critère
    sans casser l'historique (les contrôles passés gardent une copie du libellé).
    """

    class Portee(models.TextChoices):
        RECLAMATION = 'reclamation', 'Réclamation'
        DOSSIER = 'dossier', 'Dossier'
        LES_DEUX = 'les_deux', 'Les deux'

    libelle = models.CharField('libellé', max_length=255)
    portee = models.CharField(
        'portée', max_length=20, choices=Portee.choices,
        default=Portee.RECLAMATION,
        help_text="À quel flux ce critère s'applique (l'accusé : réclamation).",
    )
    actif = models.BooleanField('actif', default=True, db_index=True)
    ordre = models.PositiveIntegerField('ordre', default=0)
    cree_le = models.DateTimeField('créé le', auto_now_add=True)

    class Meta:
        verbose_name = 'critère de validation'
        verbose_name_plural = 'critères de validation'
        ordering = ['ordre', 'id']

    def __str__(self):
        return self.libelle

    def s_applique_a(self, portee):
        """Le critère s'applique-t-il à cette portée ('reclamation'/'dossier') ?"""
        return self.portee in (portee, self.Portee.LES_DEUX)


class ControleCritere(models.Model):
    """Trace d'un critère évalué lors de la validation d'une réclamation.

    Photographie à la décision : quel critère, rempli ou non, par qui. On
    conserve une copie du libellé (`libelle_snapshot`) pour rester lisible même
    si le critère est renommé ou supprimé ensuite.
    """

    reclamation = models.ForeignKey(
        ReclamationEligibilite, on_delete=models.CASCADE,
        related_name='controles', verbose_name='réclamation',
    )
    critere = models.ForeignKey(
        CritereValidation, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='controles', verbose_name='critère',
    )
    libelle_snapshot = models.CharField('libellé (copie)', max_length=255)
    rempli = models.BooleanField('rempli', default=False)
    par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='contrôlé par',
    )
    le = models.DateTimeField('le', auto_now=True)

    class Meta:
        verbose_name = 'contrôle de critère'
        verbose_name_plural = 'contrôles de critères'
        ordering = ['id']
        constraints = [
            models.UniqueConstraint(
                fields=['reclamation', 'critere'],
                name='unique_controle_reclamation_critere',
            ),
        ]

    def __str__(self):
        return f'{self.libelle_snapshot} : {"oui" if self.rempli else "non"}'


class Recours(models.Model):
    """Recours d'un candidat qui se sent lésé (souvent absent de la liste des
    retenus) alors qu'il a bien soumis un dossier ou une réclamation.

    Le demandeur recherche son identité (nom/postnom/prénom) dans la base
    (réclamations + dossiers soumis), reconnaît son enregistrement et y LIE son
    recours, puis renseigne sa date de naissance (vérification avec sa pièce
    d'identité), son email et son message. Traité dans un back-office dédié.
    """

    class Statut(models.TextChoices):
        EN_ATTENTE = 'en_attente', 'En attente'
        VALIDE = 'valide', 'Validé'
        REJETE = 'rejete', 'Rejeté'
        # Valeur historique (avant la décision valider/rejeter) : un recours
        # « traité » sans décision tranchée. Conservée pour ne pas casser les
        # enregistrements existants ; n'est plus produite par le traitement.
        TRAITE = 'traite', 'Traité'

    # Décisions qui clôturent le recours (le retirent de « En attente »).
    STATUTS_DECIDES = {Statut.VALIDE, Statut.REJETE, Statut.TRAITE}

    # Enregistrement existant reconnu par le demandeur : un dossier OU une
    # réclamation (au moins l'un des deux). SET_NULL : si la source est purgée,
    # le recours subsiste avec l'identité figée ci-dessous.
    dossier = models.ForeignKey(
        Dossier, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='recours', verbose_name='dossier lié',
    )
    reclamation = models.ForeignKey(
        'ReclamationEligibilite', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='recours', verbose_name='réclamation liée',
    )
    # Identité figée (snapshot de la source) au moment du recours.
    nom = models.CharField('nom', max_length=100)
    postnom = models.CharField('postnom', max_length=100, blank=True)
    prenom = models.CharField('prénom', max_length=100)
    # Date de naissance déclarée : sert à VÉRIFIER l'identité du demandeur
    # (recoupement avec sa pièce d'identité).
    date_naissance = models.DateField('date de naissance')
    email = models.EmailField('email de contact')
    message = models.TextField('message')
    # Domaine (poste) du recours. Par défaut hérité de la source (dossier ou
    # réclamation liée) ; un administrateur peut le corriger ici sans toucher à
    # la source. C'est ce domaine qui figure sur la liste définitive si le
    # recours est validé. NULL = on retombe sur le domaine de la source.
    poste = models.ForeignKey(
        'Poste', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='recours', verbose_name='domaine (correction)',
    )
    statut = models.CharField(
        'statut', max_length=20, choices=Statut.choices,
        default=Statut.EN_ATTENTE, db_index=True,
    )
    reponse = models.TextField('réponse / note interne', blank=True)
    # Agent (superviseur/validateur) chargé de traiter ce recours : permet de
    # répartir et d'équilibrer la charge entre plusieurs agents, comme pour les
    # dossiers et les réclamations. Un validateur ne tranche que son lot.
    affecte_a = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='recours_affectes',
        verbose_name='affecté à', db_index=True,
    )
    traite_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='recours_traites',
        verbose_name='traité par',
    )
    traite_le = models.DateTimeField('traité le', null=True, blank=True)
    cree_le = models.DateTimeField('reçu le', auto_now_add=True)

    class Meta:
        verbose_name = 'recours'
        verbose_name_plural = 'recours'
        ordering = ['-cree_le']

    def __str__(self):
        return f'Recours {self.nom} {self.prenom} — {self.get_statut_display()}'


class RetenuDefinitif(models.Model):
    """Entrée FIGÉE de la liste définitive des retenus d'un appel.

    La liste définitive = retenus publiés (dossiers RETENU) + recours VALIDÉS,
    dédupliqués par identité normalisée. Elle est générée à la publication :
    chaque personne reçoit un CODE séquentiel (0001, 0002, …) **stable et
    définitif** (les entrées déjà codées ne sont jamais renumérotées ; les
    nouvelles personnes prennent les codes suivants). On fige le nom et le
    domaine (snapshot) pour rester lisible même si la source évolue.
    """

    class Origine(models.TextChoices):
        LISTE = 'liste', 'Retenu (liste provisoire)'
        RECOURS = 'recours', 'Validé après recours'

    class Ville(models.TextChoices):
        KINSHASA = 'kinshasa', 'Kinshasa'
        LUBUMBASHI = 'lubumbashi', 'Lubumbashi'
        MBUJI_MAYI = 'mbuji_mayi', 'Mbuji-Mayi'

    class DemandeStatut(models.TextChoices):
        EN_ATTENTE = 'en_attente', 'En attente'
        VALIDEE = 'validee', 'Validée'
        REJETEE = 'rejetee', 'Rejetée'

    appel = models.ForeignKey(
        AppelCandidature, on_delete=models.CASCADE,
        related_name='retenus_definitifs', verbose_name='appel à candidature',
    )
    code = models.CharField('code', max_length=10, db_index=True)
    nom = models.CharField('nom', max_length=100)
    postnom = models.CharField('postnom', max_length=100, blank=True)
    prenom = models.CharField('prénom', max_length=100)
    poste_libelle = models.CharField('domaine', max_length=120, blank=True)
    origine = models.CharField(
        'origine', max_length=10, choices=Origine.choices, default=Origine.LISTE,
    )
    # Salle d'examen (libellé alphabétique A, B, C…), attribuée automatiquement
    # par ville selon l'ordre des codes. Vide = non encore affectée.
    salle = models.CharField('salle', max_length=4, blank=True, db_index=True)
    # Traçabilité de la source (facultative : SET_NULL pour survivre à une purge).
    dossier = models.ForeignKey(
        Dossier, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='entrees_definitives', verbose_name='dossier',
    )
    recours = models.ForeignKey(
        Recours, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='entrees_definitives', verbose_name='recours',
    )
    # Ville OFFICIELLE du test (confirmée). Kinshasa par défaut ; elle ne change
    # QUE lorsqu'un agent valide une demande (jamais directement depuis le public).
    ville_examen = models.CharField(
        'ville du test', max_length=20, choices=Ville.choices, default=Ville.KINSHASA,
    )
    # Demande de ville déposée par le candidat (formulaire public) EN ATTENTE de
    # validation par un agent. Vide = aucune demande en cours. À la validation,
    # `ville_demandee` est appliquée à `ville_examen` puis remise à vide.
    ville_demandee = models.CharField(
        'ville demandée', max_length=20, choices=Ville.choices, blank=True,
    )
    # Statut de la demande de ville : '' = aucune demande ; sinon en_attente /
    # validee / rejetee (conservé après décision pour l'historique et le filtre).
    ville_demande_statut = models.CharField(
        'statut de la demande de ville', max_length=12,
        choices=DemandeStatut.choices, blank=True, db_index=True,
    )
    ville_demandee_le = models.DateTimeField('demande reçue le', null=True, blank=True)
    # Date de naissance déclarée lors de la demande (vérification par l'agent).
    date_naissance = models.DateField('date de naissance', null=True, blank=True)
    ville_choisie_le = models.DateTimeField('ville confirmée le', null=True, blank=True)
    ville_traite_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='villes_examen_traitees', verbose_name='ville traitée par',
    )

    # Forme normalisée de « nom postnom prénom » : recherche + déduplication.
    texte_recherche = models.CharField(
        'texte de recherche', max_length=320, editable=False, db_index=True, default='',
    )
    cree_le = models.DateTimeField('créé le', auto_now_add=True)

    class Meta:
        verbose_name = 'retenu (liste définitive)'
        verbose_name_plural = 'retenus (liste définitive)'
        ordering = ['code']
        constraints = [
            models.UniqueConstraint(
                fields=['appel', 'code'], name='unique_code_definitif_par_appel',
            ),
        ]

    def save(self, *args, **kwargs):
        from .utils import normaliser_texte
        self.texte_recherche = normaliser_texte(f'{self.nom} {self.postnom} {self.prenom}')
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.code} — {self.nom} {self.postnom} {self.prenom}'.strip()
