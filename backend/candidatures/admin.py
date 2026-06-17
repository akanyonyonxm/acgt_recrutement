"""Admin Django — configuration, inspection technique et CORRECTION d'erreurs.

Le traitement métier courant (validation, examen) se fait dans l'espace Vue
dédié. La console reste cependant le lieu où un administrateur peut **corriger
une erreur** : modifier un dossier ou une réclamation (identité, code, poste,
statut…). Toute correction de **statut** d'un dossier faite ici est journalisée
dans `HistoriqueStatut` (l'audit RGPD est préservé même hors `changer_statut`).
"""

from django.contrib import admin

from .models import (
    AffectationEvaluateur,
    AppelCandidature,
    ControleCritere,
    CritereValidation,
    DocumentReclamation,
    Dossier,
    EmailQueue,
    Evaluation,
    HistoriqueStatut,
    ListeEligibilite,
    PieceExigee,
    PieceJointe,
    Poste,
    ReclamationEligibilite,
    TypePiece,
)


@admin.register(CritereValidation)
class CritereValidationAdmin(admin.ModelAdmin):
    """Grille de critères de validation — configurable (ajout/édition/suppression).

    Décocher « actif » retire le critère de la grille sans casser l'historique
    (les contrôles déjà enregistrés gardent une copie du libellé)."""

    list_display = ('libelle', 'portee', 'actif', 'ordre')
    list_editable = ('portee', 'actif', 'ordre')
    list_filter = ('actif', 'portee')
    search_fields = ('libelle',)


@admin.register(Poste)
class PosteAdmin(admin.ModelAdmin):
    list_display = ('libelle', 'actif', 'ordre')
    list_editable = ('actif', 'ordre')
    search_fields = ('libelle',)


@admin.register(EmailQueue)
class EmailQueueAdmin(admin.ModelAdmin):
    list_display = ('destinataire', 'sujet', 'statut', 'tentatives',
                    'cree_le', 'envoye_le')
    list_filter = ('statut', 'template')
    search_fields = ('destinataire', 'sujet')
    readonly_fields = ('dossier', 'destinataire', 'sujet', 'template',
                       'contexte', 'tentatives', 'cree_le', 'envoye_le')

    def has_add_permission(self, request):
        return False


@admin.register(ListeEligibilite)
class ListeEligibiliteAdmin(admin.ModelAdmin):
    list_display = ('nom', 'postnom', 'prenom', 'type_eligibilite', 'annee',
                    'reference', 'est_publie')
    list_filter = ('est_publie', 'type_eligibilite', 'annee')
    list_editable = ('est_publie',)
    search_fields = ('nom', 'postnom', 'prenom', 'reference')
    actions = ('publier', 'depublier')

    @admin.action(description='Publier la sélection (visible publiquement)')
    def publier(self, request, queryset):
        n = queryset.update(est_publie=True)
        self.message_user(request, f'{n} personne(s) publiée(s).')

    @admin.action(description='Dépublier la sélection')
    def depublier(self, request, queryset):
        n = queryset.update(est_publie=False)
        self.message_user(request, f'{n} personne(s) dépubliée(s).')


@admin.register(TypePiece)
class TypePieceAdmin(admin.ModelAdmin):
    list_display = ('libelle', 'code', 'actif', 'ordre')
    list_editable = ('actif', 'ordre')
    search_fields = ('libelle', 'code')
    prepopulated_fields = {'code': ('libelle',)}


class PieceExigeeInline(admin.TabularInline):
    model = PieceExigee
    extra = 1
    autocomplete_fields = ('type_piece',)


@admin.register(AppelCandidature)
class AppelCandidatureAdmin(admin.ModelAdmin):
    list_display = ('titre', 'statut', 'candidature_unique', 'date_ouverture',
                    'date_cloture', 'liste_retenus_publiee', 'cree_le')
    list_editable = ('candidature_unique',)
    list_filter = ('statut', 'liste_retenus_publiee', 'candidature_unique')
    search_fields = ('titre',)
    inlines = [PieceExigeeInline]


class HistoriqueStatutInline(admin.TabularInline):
    model = HistoriqueStatut
    extra = 0
    can_delete = False
    readonly_fields = ('ancien_statut', 'nouveau_statut', 'par', 'motif',
                       'horodatage')

    def has_add_permission(self, request, obj=None):
        return False


class PieceJointeInline(admin.TabularInline):
    model = PieceJointe
    extra = 0
    can_delete = False
    readonly_fields = ('type_piece', 'nom_original', 'taille', 'cree_le')
    fields = ('type_piece', 'nom_original', 'taille', 'cree_le')

    def has_add_permission(self, request, obj=None):
        return False


class AffectationInline(admin.TabularInline):
    """Désignation des évaluateurs — éditable depuis l'admin."""
    model = AffectationEvaluateur
    extra = 1
    autocomplete_fields = ('evaluateur',)
    fields = ('evaluateur', 'peut_valider', 'cree_le')
    readonly_fields = ('cree_le',)


class EvaluationInline(admin.TabularInline):
    model = Evaluation
    extra = 0
    can_delete = False
    readonly_fields = ('evaluateur', 'avis', 'recommandation', 'modifie_le')
    fields = ('evaluateur', 'recommandation', 'avis', 'modifie_le')

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Dossier)
class DossierAdmin(admin.ModelAdmin):
    """Dossier MODIFIABLE pour correction d'erreurs (identité, code, poste,
    rattachement, affectation, statut). Le changement de statut effectué ici
    est tracé dans l'historique (voir `save_model`)."""

    list_display = ('id', 'code', 'nom', 'postnom', 'prenom', 'appel', 'statut',
                    'affecte_a', 'deposant', 'cree_le')
    list_filter = ('statut', 'appel')
    search_fields = ('code', 'nom', 'postnom', 'prenom', 'email')
    # FK volumineuses (utilisateurs, liste d'éligibilité) en sélecteur « loupe ».
    raw_id_fields = ('deposant', 'affecte_a', 'ligne_eligibilite')
    # Seuls les champs calculés/horodatages restent en lecture seule.
    readonly_fields = ('texte_recherche', 'cree_le', 'modifie_le')
    inlines = [PieceJointeInline, AffectationInline, EvaluationInline,
               HistoriqueStatutInline]

    def save_model(self, request, obj, form, change):
        """Enregistre la correction et, si le statut change, le journalise.

        On contourne volontairement `changer_statut` (qui refuserait une
        transition « interdite ») : une correction d'erreur doit pouvoir
        remettre un dossier dans n'importe quel état. La traçabilité reste
        assurée par une entrée d'historique dédiée."""
        ancien = None
        if change and 'statut' in form.changed_data:
            ancien = (Dossier.objects.filter(pk=obj.pk)
                      .values_list('statut', flat=True).first())
        super().save_model(request, obj, form, change)
        if ancien is not None and ancien != obj.statut:
            HistoriqueStatut.objects.create(
                dossier=obj, ancien_statut=ancien, nouveau_statut=obj.statut,
                par=request.user,
                motif='Correction administrative via la console',
            )

    def has_add_permission(self, request):
        # Les dossiers naissent du dépôt candidat / d'une réclamation, pas de la
        # console : on n'en crée pas ici (on corrige l'existant).
        return False


class DocumentReclamationInline(admin.TabularInline):
    """Justificatifs joints à une réclamation (consultation seule)."""
    model = DocumentReclamation
    extra = 0
    can_delete = False
    readonly_fields = ('type', 'nom_original', 'taille', 'fichier', 'cree_le')
    fields = ('type', 'nom_original', 'taille', 'fichier', 'cree_le')

    def has_add_permission(self, request, obj=None):
        return False


class ControleCritereInline(admin.TabularInline):
    """Grille de critères telle que cochée à la validation (consultation)."""
    model = ControleCritere
    extra = 0
    can_delete = False
    readonly_fields = ('libelle_snapshot', 'rempli', 'par', 'le')
    fields = ('libelle_snapshot', 'rempli', 'par', 'le')

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ReclamationEligibilite)
class ReclamationEligibiliteAdmin(admin.ModelAdmin):
    """Réclamation MODIFIABLE et CRÉABLE pour corriger/saisir manuellement
    (identité, poste, statut, affectation). Les justificatifs sont consultables
    en bas de fiche.

    Note : créer/modifier ici ne reproduit PAS l'effet métier de la validation
    via l'app (qui crée le dossier RETENU). C'est un outil de correction et de
    saisie, pas le circuit de traitement normal. Une réclamation saisie ici
    arrive « en attente » et sera traitée comme les autres."""

    list_display = ('id', 'nom', 'postnom', 'prenom', 'appel', 'statut',
                    'affecte_a', 'traite_par', 'cree_le')
    list_filter = ('statut', 'appel')
    search_fields = ('nom', 'postnom', 'prenom', 'email')
    raw_id_fields = ('affecte_a', 'traite_par', 'dossier_cree')
    readonly_fields = ('texte_recherche', 'cree_le')
    inlines = [DocumentReclamationInline, ControleCritereInline]
