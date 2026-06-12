from rest_framework import serializers

from .models import (
    TAILLE_MAX_PIECE,
    AffectationEvaluateur,
    AppelCandidature,
    Dossier,
    Evaluation,
    HistoriqueStatut,
    DocumentReclamation,
    ListeEligibilite,
    PieceExigee,
    PieceJointe,
    Poste,
    ReclamationEligibilite,
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
    """Vue publique : CODE · NOM · POSTNOM · PRÉNOM (rien de sensible)."""

    class Meta:
        model = ListeEligibilite
        fields = ['id', 'code', 'nom', 'postnom', 'prenom']


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
            'id', 'code', 'nom', 'postnom', 'prenom', 'type_eligibilite',
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
    # Ligne d'éligibilité dont le code correspond exactement au code saisi
    # (suggestion de rattachement en un clic ; jamais de comparaison de noms).
    suggestion_eligibilite = serializers.SerializerMethodField()
    # Personnes de la liste d'éligibilité qui correspondent au dossier (par code
    # ou par nom), avec comparaison champ par champ — affiché automatiquement à
    # l'ouverture pour décider vite. Détail uniquement (une seule requête).
    candidats_eligibilite = serializers.SerializerMethodField()
    # Autres dossiers du même appel = même personne probable (même email ou même
    # nom complet normalisé) — pour repérer et traiter les doublons.
    doublons = serializers.SerializerMethodField()

    class Meta:
        model = Dossier
        fields = [
            'id', 'code', 'appel', 'appel_titre', 'poste', 'poste_libelle', 'deposant',
            'nom', 'postnom', 'prenom', 'email', 'statut', 'statut_libelle',
            'transitions_possibles', 'ligne_eligibilite', 'suggestion_eligibilite',
            'candidats_eligibilite', 'doublons', 'pieces', 'pieces_manquantes',
            'est_complet', 'modifiable', 'cree_le', 'modifie_le',
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

    def get_suggestion_eligibilite(self, obj):
        # Suggestion uniquement si pas déjà rattaché et si le code saisi
        # correspond à UNE seule ligne (un code ambigu ne suggère rien).
        if obj.ligne_eligibilite_id or not (obj.code or '').strip():
            return None
        lignes = list(
            ListeEligibilite.objects.filter(code__iexact=obj.code.strip())[:2]
        )
        if len(lignes) != 1:
            return None
        ligne = lignes[0]
        return {
            'id': ligne.id, 'code': ligne.code, 'nom': ligne.nom,
            'postnom': ligne.postnom, 'prenom': ligne.prenom,
        }

    def get_candidats_eligibilite(self, obj):
        """Lignes de la liste correspondant au dossier (code OU un des noms),
        avec comparaison champ par champ. Triées par nombre de champs en commun.
        Calculé pour le détail uniquement (une seule ligne → une requête)."""
        from functools import reduce
        import operator
        from django.db.models import Q

        code = (obj.code or '').strip()
        conds = []
        if code:
            conds.append(Q(code__iexact=code))
        if obj.nom:
            conds.append(Q(nom__iexact=obj.nom))
        if obj.postnom:
            conds.append(Q(postnom__iexact=obj.postnom))
        if obj.prenom:
            conds.append(Q(prenom__iexact=obj.prenom))
        if not conds:
            return []

        def egal(a, b):
            return bool(a) and bool(b) and a.strip().lower() == b.strip().lower()

        resultats = []
        for ligne in ListeEligibilite.objects.filter(reduce(operator.or_, conds))[:30]:
            match = {
                'code': egal(ligne.code, code),
                'nom': egal(ligne.nom, obj.nom),
                'postnom': egal(ligne.postnom, obj.postnom),
                'prenom': egal(ligne.prenom, obj.prenom),
            }
            resultats.append({
                'id': ligne.id, 'code': ligne.code, 'nom': ligne.nom,
                'postnom': ligne.postnom, 'prenom': ligne.prenom,
                'match': match, 'score': sum(match.values()),
            })
        resultats.sort(key=lambda r: r['score'], reverse=True)
        return resultats[:6]

    def get_doublons(self, obj):
        """Autres dossiers SOUMIS du même appel ayant le même NOM COMPLET
        (nom+postnom+prénom normalisé) = même personne probable. On n'utilise
        pas l'email (un proche peut déposer pour plusieurs personnes depuis la
        même adresse). Les brouillons sont ignorés."""
        if not obj.texte_recherche:
            return []
        autres = (
            Dossier.objects
            .filter(appel_id=obj.appel_id, texte_recherche=obj.texte_recherche)
            .exclude(statut=Dossier.Statut.BROUILLON)   # on ignore les brouillons
            .exclude(pk=obj.pk)
            .order_by('cree_le')[:10]
        )
        return [
            {
                'id': d.id, 'code': d.code, 'nom': d.nom, 'postnom': d.postnom,
                'prenom': d.prenom, 'email': d.email, 'statut': d.statut,
                'statut_libelle': d.get_statut_display(),
                'meme_email': (d.email or '').strip().lower() == (obj.email or '').strip().lower(),
            }
            for d in autres
        ]

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
    # Correspondance avec la liste d'éligibilité (badge indicatif, jamais
    # bloquant). Renvoie { etat, champs } :
    #   etat='rattache'     déjà relié à une personne de la liste ;
    #   etat='a_rattacher'  nom complet trouvé sur la liste (prêt à rattacher) ;
    #   etat='champs'       liste des champs qui coïncident (code/nom/postnom/prenom) ;
    #   etat='aucune'       rien ne correspond.
    # S'appuie sur les annotations du queryset.
    correspondance = serializers.SerializerMethodField()
    # Doublon probable (autre dossier du même appel, même email ou même nom).
    a_doublon = serializers.BooleanField(read_only=True, default=False)
    # Nom complet tel qu'il figure sur la liste d'éligibilité :
    #   - si rattaché : la personne liée ;
    #   - sinon, si le code saisi est reconnu : le propriétaire de ce code
    #     (révèle un éventuel décalage nom saisi / nom de la liste — triche).
    # `rattache` indique lequel des deux cas (pour l'affichage côté front).
    eligibilite_nom = serializers.SerializerMethodField()

    class Meta:
        model = Dossier
        fields = [
            'id', 'code', 'appel', 'appel_titre', 'poste_libelle', 'nom', 'postnom', 'prenom',
            'statut', 'statut_libelle', 'correspondance', 'a_doublon',
            'eligibilite_nom', 'cree_le',
        ]

    def get_eligibilite_nom(self, obj):
        ligne = obj.ligne_eligibilite   # select_related dans get_queryset
        rattache = ligne is not None
        if ligne is None:
            code = (obj.code or '').strip()
            if code:
                lignes = list(ListeEligibilite.objects.filter(code__iexact=code)[:2])
                if len(lignes) == 1:
                    ligne = lignes[0]
        if ligne is None:
            return None
        return {
            'nom': f'{ligne.nom} {ligne.postnom} {ligne.prenom}'.strip(),
            'code': ligne.code,
            'rattache': rattache,
        }

    def get_correspondance(self, obj):
        if obj.ligne_eligibilite_id:
            return {'etat': 'rattache', 'champs': []}
        # Nom complet trouvé sur la liste → prêt à rattacher (la personne y est).
        if getattr(obj, 'corresp_nom_complet', False):
            return {'etat': 'a_rattacher', 'champs': []}
        # Sinon, on liste précisément les champs qui coïncident.
        champs = []
        if getattr(obj, 'corresp_code', False):
            champs.append('code')
        if getattr(obj, 'corresp_f_nom', False):
            champs.append('nom')
        if getattr(obj, 'corresp_f_postnom', False):
            champs.append('postnom')
        if getattr(obj, 'corresp_f_prenom', False):
            champs.append('prenom')
        if not champs:
            return {'etat': 'aucune', 'champs': []}
        return {'etat': 'champs', 'champs': champs}


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


class ReclamationCreationSerializer(serializers.ModelSerializer):
    """Champs texte d'une réclamation publique. Les fichiers (accusé, CV, pièce
    d'identité, diplômes) sont validés et créés par la vue (multi-fichiers)."""

    # Champ honeypot anti-spam : doit rester vide (les bots le remplissent).
    site_web = serializers.CharField(required=False, allow_blank=True, write_only=True)
    # Message obligatoire (le modèle l'autorise vide, on l'exige à la saisie).
    message = serializers.CharField(required=True, allow_blank=False)
    # Poste souhaité : obligatoire à la saisie (le modèle reste nullable pour
    # les réclamations antérieures à ce champ).
    poste = serializers.PrimaryKeyRelatedField(
        queryset=Poste.objects.filter(actif=True), required=True,
    )

    class Meta:
        model = ReclamationEligibilite
        fields = [
            'id', 'appel', 'poste', 'nom', 'postnom', 'prenom', 'email',
            'telephone', 'message', 'site_web',
        ]

    def validate_appel(self, appel):
        if appel.statut != AppelCandidature.Statut.PUBLIE:
            raise serializers.ValidationError(
                "Cet appel à candidature n'est pas ouvert."
            )
        return appel

    def validate_site_web(self, valeur):
        if valeur:
            raise serializers.ValidationError("Requête invalide.")
        return valeur

    def create(self, validated_data):
        # Le honeypot n'est pas un champ du modèle : on le retire avant création.
        validated_data.pop('site_web', None)
        return super().create(validated_data)


class DocumentReclamationSerializer(serializers.ModelSerializer):
    type_libelle = serializers.CharField(source='get_type_display', read_only=True)

    class Meta:
        model = DocumentReclamation
        fields = ['id', 'type', 'type_libelle', 'nom_original', 'taille']


class ReclamationAdminSerializer(serializers.ModelSerializer):
    """Vue back-office d'une réclamation (sans exposer les URL fichier)."""

    statut_libelle = serializers.CharField(source='get_statut_display', read_only=True)
    appel_titre = serializers.CharField(source='appel.titre', read_only=True)
    poste_libelle = serializers.CharField(source='poste.libelle', read_only=True, default=None)
    traite_par = serializers.StringRelatedField(read_only=True)
    dossier_cree_id = serializers.IntegerField(source='dossier_cree.id', read_only=True, default=None)
    documents = DocumentReclamationSerializer(many=True, read_only=True)

    class Meta:
        model = ReclamationEligibilite
        fields = [
            'id', 'appel', 'appel_titre', 'poste', 'poste_libelle',
            'nom', 'postnom', 'prenom', 'email',
            'telephone', 'message', 'documents', 'statut', 'statut_libelle',
            'motif', 'traite_par', 'traite_le', 'dossier_cree_id', 'cree_le',
        ]
