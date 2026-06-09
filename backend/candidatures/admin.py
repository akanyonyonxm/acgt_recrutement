"""Admin Django — réservé à la configuration et à l'inspection technique.

Le traitement métier des dossiers (validation, examen) se fait dans l'espace
Vue dédié, pas ici. Les dossiers et leur historique sont donc en lecture seule.
"""

from django.contrib import admin

from .models import (
    AffectationEvaluateur,
    AppelCandidature,
    Dossier,
    EmailQueue,
    Evaluation,
    HistoriqueStatut,
    ListeEligibilite,
    PieceExigee,
    PieceJointe,
    Poste,
    TypePiece,
)


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
    list_display = ('id', 'nom', 'postnom', 'prenom', 'appel', 'statut',
                    'deposant', 'cree_le')
    list_filter = ('statut', 'appel')
    search_fields = ('nom', 'postnom', 'prenom', 'email')
    readonly_fields = ('appel', 'deposant', 'nom', 'postnom', 'prenom', 'email',
                       'statut', 'ligne_eligibilite', 'cree_le', 'modifie_le')
    inlines = [PieceJointeInline, AffectationInline, EvaluationInline,
               HistoriqueStatutInline]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
