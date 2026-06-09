from rest_framework import serializers

from .models import (
    TAILLE_MAX_PIECE,
    AffectationEvaluateur,
    AppelCandidature,
    Dossier,
    Evaluation,
    HistoriqueStatut,
    ListeEligibilite,
    PieceExigee,
    PieceJointe,
    Poste,
    TypePiece,
)


class TypePieceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TypePiece
        fields = ['id', 'code', 'libelle', 'description', 'ordre']


class PosteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Poste
        fields = ['id', 'libelle', 'description', 'ordre']


class EligibilitePubliqueSerializer(serializers.ModelSerializer):
    """Vue publique : strictement NOM · POSTNOM · PRÉNOM (rien de sensible)."""

    class Meta:
        model = ListeEligibilite
        fields = ['id', 'nom', 'postnom', 'prenom']


class RetenuPubliqueSerializer(serializers.ModelSerializer):
    """Vue publique d'une personne retenue : NOM · POSTNOM · PRÉNOM seulement."""

    class Meta:
        model = Dossier
        fields = ['id', 'nom', 'postnom', 'prenom']


class EligibiliteAdminSerializer(serializers.ModelSerializer):
    """Vue admin : tous les champs, y compris la référence interne."""

    type_libelle = serializers.CharField(
        source='get_type_eligibilite_display', read_only=True,
    )

    class Meta:
        model = ListeEligibilite
        fields = [
            'id', 'nom', 'postnom', 'prenom', 'type_eligibilite',
            'type_libelle', 'annee', 'reference', 'est_publie',
        ]


class PieceExigeeSerializer(serializers.ModelSerializer):
    type_piece = TypePieceSerializer(read_only=True)

    class Meta:
        model = PieceExigee
        fields = ['id', 'type_piece', 'obligatoire', 'multiple', 'ordre']


class HistoriqueStatutSerializer(serializers.ModelSerializer):
    par = serializers.StringRelatedField()
    ancien_statut_libelle = serializers.CharField(
        source='get_ancien_statut_display', read_only=True,
    )
    nouveau_statut_libelle = serializers.CharField(
        source='get_nouveau_statut_display', read_only=True,
    )

    class Meta:
        model = HistoriqueStatut
        fields = [
            'id', 'ancien_statut', 'ancien_statut_libelle',
            'nouveau_statut', 'nouveau_statut_libelle',
            'par', 'motif', 'horodatage',
        ]


class PieceJointeSerializer(serializers.ModelSerializer):
    """Représentation d'une pièce déjà déposée (sans exposer l'URL fichier)."""

    type_piece = TypePieceSerializer(read_only=True)

    class Meta:
        model = PieceJointe
        fields = ['id', 'type_piece', 'nom_original', 'taille', 'cree_le']


class PieceJointeUploadSerializer(serializers.ModelSerializer):
    """Ajout d'une pièce à un dossier brouillon."""

    type_piece = serializers.PrimaryKeyRelatedField(
        queryset=TypePiece.objects.filter(actif=True),
    )

    class Meta:
        model = PieceJointe
        fields = ['id', 'type_piece', 'fichier']

    def validate_fichier(self, fichier):
        if fichier.size > TAILLE_MAX_PIECE:
            limite = TAILLE_MAX_PIECE // (1024 * 1024)
            raise serializers.ValidationError(
                f"Fichier trop volumineux (max {limite} Mo)."
            )
        return fichier


class DossierSerializer(serializers.ModelSerializer):
    statut_libelle = serializers.CharField(
        source='get_statut_display', read_only=True,
    )
    deposant = serializers.StringRelatedField(read_only=True)
    appel_titre = serializers.CharField(source='appel.titre', read_only=True)
    poste_libelle = serializers.CharField(source='poste.libelle', read_only=True, default=None)
    ligne_eligibilite = serializers.StringRelatedField(read_only=True)
    pieces = PieceJointeSerializer(many=True, read_only=True)
    # Pièces obligatoires encore manquantes (libellés) — pilote le bouton
    # « soumettre » côté front.
    pieces_manquantes = serializers.SerializerMethodField()
    est_complet = serializers.BooleanField(read_only=True)
    modifiable = serializers.BooleanField(read_only=True)
    # Statuts atteignables depuis l'état courant — utile au front pour n'afficher
    # que les actions réellement possibles.
    transitions_possibles = serializers.SerializerMethodField()

    class Meta:
        model = Dossier
        fields = [
            'id', 'appel', 'appel_titre', 'poste', 'poste_libelle', 'deposant',
            'nom', 'postnom', 'prenom', 'email', 'statut', 'statut_libelle',
            'transitions_possibles', 'ligne_eligibilite', 'pieces',
            'pieces_manquantes', 'est_complet', 'modifiable', 'cree_le', 'modifie_le',
        ]
        # Le statut ne se change jamais par PATCH direct : il passe par les
        # actions dédiées (soumettre / approuver / rejeter / retenir / …).
        read_only_fields = [
            'statut', 'deposant', 'ligne_eligibilite', 'cree_le', 'modifie_le',
        ]

    def get_transitions_possibles(self, obj):
        return sorted(obj.transitions_possibles())

    def get_pieces_manquantes(self, obj):
        return [tp.libelle for tp in obj.pieces_obligatoires_manquantes()]

    def validate_appel(self, appel):
        # On ne dépose que sur un appel à candidature ouvert (publié).
        if appel.statut != AppelCandidature.Statut.PUBLIE:
            raise serializers.ValidationError(
                "Cet appel à candidature n'est pas ouvert aux dépôts."
            )
        return appel


class DossierListeSerializer(serializers.ModelSerializer):
    """Vue allégée pour les listes (évite le N+1 des pièces/complétude)."""

    statut_libelle = serializers.CharField(
        source='get_statut_display', read_only=True,
    )
    appel_titre = serializers.CharField(source='appel.titre', read_only=True)
    poste_libelle = serializers.CharField(source='poste.libelle', read_only=True, default=None)

    class Meta:
        model = Dossier
        fields = [
            'id', 'appel', 'appel_titre', 'poste_libelle', 'nom', 'postnom', 'prenom',
            'statut', 'statut_libelle', 'cree_le',
        ]


class ChangementStatutSerializer(serializers.Serializer):
    """Corps des actions de transition : motif optionnel (obligatoire au rejet)."""

    motif = serializers.CharField(required=False, allow_blank=True, default='')


class AffectationSerializer(serializers.ModelSerializer):
    evaluateur = serializers.StringRelatedField(read_only=True)
    evaluateur_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = AffectationEvaluateur
        fields = ['id', 'evaluateur', 'evaluateur_id', 'peut_valider', 'cree_le']


class EvaluationSerializer(serializers.ModelSerializer):
    evaluateur = serializers.StringRelatedField(read_only=True)
    recommandation_libelle = serializers.CharField(
        source='get_recommandation_display', read_only=True,
    )

    class Meta:
        model = Evaluation
        fields = [
            'id', 'evaluateur', 'avis', 'recommandation',
            'recommandation_libelle', 'cree_le', 'modifie_le',
        ]
        read_only_fields = ['evaluateur', 'cree_le', 'modifie_le']


class AppelCandidatureSerializer(serializers.ModelSerializer):
    statut_libelle = serializers.CharField(
        source='get_statut_display', read_only=True,
    )
    # Alimenté par l'annotation du queryset (évite un COUNT par AAC en liste).
    nb_dossiers = serializers.IntegerField(read_only=True)
    pieces_exigees = PieceExigeeSerializer(many=True, read_only=True)

    class Meta:
        model = AppelCandidature
        fields = [
            'id', 'titre', 'description', 'statut', 'statut_libelle',
            'date_ouverture', 'date_cloture', 'liste_retenus_publiee',
            'candidature_unique', 'pieces_exigees', 'nb_dossiers',
            'cree_le', 'modifie_le',
        ]
