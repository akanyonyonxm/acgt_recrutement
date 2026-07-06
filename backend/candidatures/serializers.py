from django.db.models import Q
from rest_framework import serializers

from .models import (
    TAILLE_MAX_PIECE,
    AffectationEvaluateur,
    AppelCandidature,
    ControleCritere,
    CritereValidation,
    Dossier,
    Evaluation,
    HistoriqueStatut,
    DocumentReclamation,
    ListeEligibilite,
    PieceExigee,
    PieceJointe,
    Poste,
    ReclamationEligibilite,
    Recours,
    RetenuDefinitif,
    TypePiece,
)


class CritereValidationSerializer(serializers.ModelSerializer):
    """Critère de la grille de validation (lecture pour le front)."""

    class Meta:
        model = CritereValidation
        fields = ['id', 'libelle', 'portee', 'ordre']


class ControleCritereSerializer(serializers.ModelSerializer):
    """Contrôle enregistré d'un critère (affiché sur une réclamation décidée)."""

    class Meta:
        model = ControleCritere
        fields = ['id', 'critere', 'libelle_snapshot', 'rempli']


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
    """Vue publique d'une personne retenue : NOM · POSTNOM · PRÉNOM · POSTE."""

    poste_libelle = serializers.CharField(source='poste.libelle', read_only=True, default=None)

    class Meta:
        model = Dossier
        fields = ['id', 'nom', 'postnom', 'prenom', 'poste_libelle']


class RetenuDefinitifSerializer(serializers.ModelSerializer):
    """Vue publique d'une entrée de la liste DÉFINITIVE : CODE + identité +
    domaine. Le code est figé à la publication (stable et définitif)."""

    ville_examen_libelle = serializers.CharField(source='get_ville_examen_display', read_only=True)
    interview_date_libelle = serializers.SerializerMethodField()

    class Meta:
        model = RetenuDefinitif
        fields = ['id', 'code', 'nom', 'postnom', 'prenom', 'poste_libelle', 'origine',
                  'ville_examen', 'ville_examen_libelle', 'salle',
                  'interview_date', 'interview_date_libelle', 'interview_heure']

    _MOIS = ['', 'janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet',
             'août', 'septembre', 'octobre', 'novembre', 'décembre']
    _JOURS = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche']

    def get_interview_date_libelle(self, obj):
        d = obj.interview_date
        if not d:
            return ''
        return f"{self._JOURS[d.weekday()]} {d.day:02d} {self._MOIS[d.month]} {d.year}"


class RetenuSupplementSerializer(serializers.ModelSerializer):
    """Ajout SUPPLÉMENTAIRE à la liste définitive (back-office). Le code, la salle
    et l'origine sont gérés par la vue (non modifiables ici)."""

    ville_examen_libelle = serializers.CharField(source='get_ville_examen_display', read_only=True)

    class Meta:
        model = RetenuDefinitif
        fields = ['id', 'appel', 'code', 'nom', 'postnom', 'prenom', 'poste_libelle',
                  'ville_examen', 'ville_examen_libelle', 'salle', 'origine']
        # La salle est saisissable ICI (attribution manuelle d'un supplément, sans
        # relancer la répartition globale qui réécrirait toute la ville).
        read_only_fields = ['code', 'origine']

    def validate_salle(self, v):
        return (v or '').strip().upper()[:4]

    def validate_nom(self, v):
        if not (v or '').strip():
            raise serializers.ValidationError("Le nom est requis.")
        return v.strip()

    def validate_prenom(self, v):
        if not (v or '').strip():
            raise serializers.ValidationError("Le prénom est requis.")
        return v.strip()


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


class MasquageDecisionMixin:
    """Masque l'état d'un dossier SOUMIS au CANDIDAT tant que les résultats de
    l'appel ne sont pas publiés.

    Tant que la liste n'est pas publiée, tout dossier soumis (déposé, en examen,
    ou déjà décidé) est présenté au candidat comme « En cours de traitement »
    (statut neutre EN_EXAMEN). Seul BROUILLON garde son état (le candidat le
    construit encore). Une fois publiée, le vrai statut/décision s'affiche.
    Le personnel back-office (et les comptes techniques) voient toujours le vrai
    statut. À utiliser avec `statut` et `statut_libelle` en SerializerMethodField.
    """

    def _est_staff(self):
        # Mis en cache sur l'instance (réutilisée pour tous les items en liste).
        if not hasattr(self, '_staff_cache'):
            from . import roles
            request = self.context.get('request')
            user = getattr(request, 'user', None)
            self._staff_cache = bool(
                user and user.is_authenticated and roles.acces_backoffice(user)
            )
        return self._staff_cache

    def _decision_masquee(self, obj):
        if self._est_staff():
            return False
        # Tout sauf le brouillon est « en cours de traitement » jusqu'à publication.
        return (obj.statut != Dossier.Statut.BROUILLON
                and not obj.appel.liste_retenus_publiee)

    def get_statut(self, obj):
        return 'en_examen' if self._decision_masquee(obj) else obj.statut

    def get_statut_libelle(self, obj):
        if self._decision_masquee(obj):
            return 'En cours de traitement'
        return obj.get_statut_display()


class DossierSerializer(MasquageDecisionMixin, serializers.ModelSerializer):
    statut = serializers.SerializerMethodField()
    statut_libelle = serializers.SerializerMethodField()
    deposant = serializers.StringRelatedField(read_only=True)
    appel_titre = serializers.CharField(source='appel.titre', read_only=True)
    poste_libelle = serializers.CharField(source='poste.libelle', read_only=True, default=None)
    ligne_eligibilite = serializers.StringRelatedField(read_only=True)
    # Agent chargé du dossier (répartition) ; nom lisible pour l'affichage.
    affecte_a_nom = serializers.SerializerMethodField()
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
            'affecte_a', 'affecte_a_nom',
            'est_complet', 'modifiable', 'cree_le', 'modifie_le',
        ]
        # Le statut ne se change jamais par PATCH direct : il passe par les
        # actions dédiées (soumettre / approuver / rejeter / retenir / …) — et
        # c'est désormais un SerializerMethodField (masquage candidat).
        # `affecte_a` se change via l'action `repartir` (jamais par PATCH).
        read_only_fields = [
            'deposant', 'ligne_eligibilite', 'affecte_a',
            'cree_le', 'modifie_le',
        ]

    # Champs réservés au BACK-OFFICE : jamais exposés au candidat (nom de
    # l'agent, rattachement/correspondances d'éligibilité, autres dossiers…).
    CHAMPS_STAFF = (
        'affecte_a', 'affecte_a_nom', 'ligne_eligibilite', 'suggestion_eligibilite',
        'candidats_eligibilite', 'doublons',
    )

    def to_representation(self, obj):
        data = super().to_representation(obj)
        if not self._est_staff():
            for champ in self.CHAMPS_STAFF:
                data.pop(champ, None)
        return data

    def get_affecte_a_nom(self, obj):
        if not self._est_staff():
            return None
        u = obj.affecte_a
        return (u.get_full_name() or u.email) if u else None

    def get_transitions_possibles(self, obj):
        # Décision masquée au candidat : ne révèle aucune transition.
        if self._decision_masquee(obj):
            return []
        return sorted(obj.transitions_possibles())

    def get_pieces_manquantes(self, obj):
        return [tp.libelle for tp in obj.pieces_obligatoires_manquantes()]

    def get_suggestion_eligibilite(self, obj):
        # Réservé au back-office (et inutile au candidat).
        if not self._est_staff():
            return None
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
        if not self._est_staff():
            return []
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
        if not self._est_staff():
            return []
        if not obj.texte_recherche:
            return []
        autres = (
            Dossier.objects
            .filter(appel_id=obj.appel_id, texte_recherche=obj.texte_recherche)
            # On ignore les brouillons (non traités) et les rejetés (déjà écartés,
            # ex. doublon déjà traité).
            .exclude(statut__in=[Dossier.Statut.BROUILLON, Dossier.Statut.REJETE])
            .exclude(pk=obj.pk)
            .order_by('cree_le')[:10]
        )
        return [
            {
                'id': d.id, 'code': d.code, 'nom': d.nom, 'postnom': d.postnom,
                'prenom': d.prenom, 'email': d.email, 'statut': d.statut,
                'statut_libelle': d.get_statut_display(),
                'affecte_a': d.affecte_a_id,
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


class DossierListeSerializer(MasquageDecisionMixin, serializers.ModelSerializer):
    """Vue allégée pour les listes (évite le N+1 des pièces/complétude)."""

    statut = serializers.SerializerMethodField()
    statut_libelle = serializers.SerializerMethodField()
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
    # Agent affecté au dossier (répartition de la charge).
    affecte_a = serializers.IntegerField(source='affecte_a_id', read_only=True, default=None)
    affecte_a_nom = serializers.SerializerMethodField()

    class Meta:
        model = Dossier
        fields = [
            'id', 'code', 'appel', 'appel_titre', 'poste_libelle',
            'nom', 'postnom', 'prenom',
            'statut', 'statut_libelle', 'correspondance', 'a_doublon',
            'eligibilite_nom', 'affecte_a', 'affecte_a_nom', 'cree_le',
        ]

    # Champs réservés au BACK-OFFICE : jamais exposés au candidat.
    CHAMPS_STAFF = ('affecte_a', 'affecte_a_nom', 'eligibilite_nom',
                    'correspondance', 'a_doublon')

    def to_representation(self, obj):
        data = super().to_representation(obj)
        if not self._est_staff():
            for champ in self.CHAMPS_STAFF:
                data.pop(champ, None)
        return data

    def get_affecte_a_nom(self, obj):
        if not self._est_staff():
            return None
        u = obj.affecte_a
        return (u.get_full_name() or u.email) if u else None

    @staticmethod
    def _nb_champs_communs(ligne, obj):
        """Nombre de champs de nom identiques (insensible casse) entre une ligne
        d'éligibilité et le dossier — pour choisir le meilleur candidat partiel."""
        def egal(a, b):
            return bool(a) and bool(b) and a.strip().lower() == b.strip().lower()
        return (egal(ligne.nom, obj.nom) + egal(ligne.postnom, obj.postnom)
                + egal(ligne.prenom, obj.prenom))

    def get_eligibilite_nom(self, obj):
        if not self._est_staff():
            return None
        ligne = obj.ligne_eligibilite   # select_related dans get_queryset
        if ligne is not None:
            return {
                'nom': f'{ligne.nom} {ligne.postnom} {ligne.prenom}'.strip(),
                'code': ligne.code, 'rattache': True, 'partiel': False,
            }
        # Hors rattachement, on s'appuie UNIQUEMENT sur les champs de nom
        # (nom/postnom/prénom), JAMAIS sur le code seul : le code peut appartenir
        # à quelqu'un d'autre (triche).
        # 1) Nom complet identique → « à rattacher » (très probablement la personne).
        if getattr(obj, 'corresp_nom_complet', False) and obj.texte_recherche:
            lignes = list(
                ListeEligibilite.objects.filter(texte_recherche=obj.texte_recherche)[:2]
            )
            if len(lignes) == 1:
                ligne = lignes[0]
                return {
                    'nom': f'{ligne.nom} {ligne.postnom} {ligne.prenom}'.strip(),
                    'code': ligne.code, 'rattache': False, 'partiel': False,
                }
        # 2) Correspondance partielle : on montre le meilleur candidat pour aider
        # à repérer une coquille, MAIS seulement s'il partage AU MOINS 2 champs de
        # nom (nom+postnom ou nom+prénom). Un seul champ commun (ex. un prénom
        # courant) ramènerait n'importe qui → bruit. Jamais via le code.
        if (getattr(obj, 'corresp_f_nom', False) or getattr(obj, 'corresp_f_postnom', False)
                or getattr(obj, 'corresp_f_prenom', False)):
            conds = Q()
            if obj.nom:
                conds |= Q(nom__iexact=obj.nom)
            if obj.postnom:
                conds |= Q(postnom__iexact=obj.postnom)
            if obj.prenom:
                conds |= Q(prenom__iexact=obj.prenom)
            candidats = list(ListeEligibilite.objects.filter(conds)[:8])
            if candidats:
                ligne = max(candidats, key=lambda l: self._nb_champs_communs(l, obj))
                if self._nb_champs_communs(ligne, obj) >= 2:
                    return {
                        'nom': f'{ligne.nom} {ligne.postnom} {ligne.prenom}'.strip(),
                        'code': ligne.code, 'rattache': False, 'partiel': True,
                    }
        return None

    def get_correspondance(self, obj):
        if obj.ligne_eligibilite_id:
            return {'etat': 'rattache', 'champs': []}
        # Nom complet trouvé sur la liste → prêt à rattacher (la personne y est).
        if getattr(obj, 'corresp_nom_complet', False):
            return {'etat': 'a_rattacher', 'champs': []}
        # Correspondance partielle = au moins un champ de NOM coïncide. Le code
        # seul (sans aucun champ de nom) ne compte PAS : il peut appartenir à
        # quelqu'un d'autre (triche) → traité comme « aucune ».
        champs_nom = []
        if getattr(obj, 'corresp_f_nom', False):
            champs_nom.append('nom')
        if getattr(obj, 'corresp_f_postnom', False):
            champs_nom.append('postnom')
        if getattr(obj, 'corresp_f_prenom', False):
            champs_nom.append('prenom')
        if not champs_nom:
            return {'etat': 'aucune', 'champs': []}
        # Le code est affiché en complément s'il coïncide aussi (info utile).
        champs = (['code'] if getattr(obj, 'corresp_code', False) else []) + champs_nom
        return {'etat': 'champs', 'champs': champs}


class ModificationIdentiteSerializer(serializers.ModelSerializer):
    """Correction de l'identité d'un dossier (code, nom, postnom, prénom).

    Réservé aux administrateurs et correcteurs. `save()` recalcule
    automatiquement `texte_recherche` (recherche et doublons restent cohérents)."""

    class Meta:
        model = Dossier
        fields = ['code', 'nom', 'postnom', 'prenom']

    def validate_nom(self, v):
        if not (v or '').strip():
            raise serializers.ValidationError("Le nom est obligatoire.")
        return v

    def validate_prenom(self, v):
        if not (v or '').strip():
            raise serializers.ValidationError("Le prénom est obligatoire.")
        return v


class ModificationNomEligibiliteSerializer(serializers.ModelSerializer):
    """Correction du nom d'une personne de la liste d'éligibilité.

    Le code n'est volontairement PAS modifiable (identifiant stable). `save()`
    recalcule `texte_recherche` (les correspondances restent cohérentes)."""

    class Meta:
        model = ListeEligibilite
        fields = ['nom', 'postnom', 'prenom']

    def validate_nom(self, v):
        if not (v or '').strip():
            raise serializers.ValidationError("Le nom est obligatoire.")
        return v


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
            'message_retenus', 'liste_definitive_publiee', 'message_retenus_definitif',
            'instructions_examen', 'afficher_salle_public', 'afficher_supplements_definitif',
            'liste_interview_publiee', 'message_interview',
            'date_limite_recours', 'candidature_unique',
            'pieces_exigees', 'nb_dossiers', 'cree_le', 'modifie_le',
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
        if not appel.est_ouvert:
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
    affecte_a_nom = serializers.SerializerMethodField()
    controles = ControleCritereSerializer(many=True, read_only=True)
    dossier_cree_id = serializers.IntegerField(source='dossier_cree.id', read_only=True, default=None)
    documents = DocumentReclamationSerializer(many=True, read_only=True)
    # Doublon probable (autre réclamation du même appel, même nom complet).
    a_doublon = serializers.BooleanField(read_only=True, default=False)
    # La personne a déjà un dossier DÉPOSÉ (même nom) → réclamation redondante.
    a_dossier_depose = serializers.BooleanField(read_only=True, default=False)

    class Meta:
        model = ReclamationEligibilite
        fields = [
            'id', 'appel', 'appel_titre', 'poste', 'poste_libelle',
            'nom', 'postnom', 'prenom', 'email',
            'telephone', 'message', 'documents', 'statut', 'statut_libelle',
            'motif', 'traite_par', 'traite_le', 'dossier_cree_id',
            'affecte_a', 'affecte_a_nom', 'controles',
            'a_doublon', 'a_dossier_depose', 'cree_le',
        ]
        read_only_fields = ['affecte_a']

    def get_affecte_a_nom(self, obj):
        u = obj.affecte_a
        if not u:
            return None
        return (u.get_full_name() or u.email)


class RecoursCreationSerializer(serializers.ModelSerializer):
    """Dépôt public d'un recours, LIÉ à un enregistrement existant.

    Le demandeur fournit la source qu'il a reconnue (`source_type` =
    dossier|reclamation, `source_id`) + date de naissance + email + message.
    L'identité est figée depuis la source (jamais saisie librement)."""

    source_type = serializers.ChoiceField(choices=['dossier', 'reclamation'], write_only=True)
    source_id = serializers.IntegerField(write_only=True)
    date_naissance = serializers.DateField(
        required=True, allow_null=False,
        error_messages={
            'required': "La date de naissance est requise (vérification d'identité).",
            'null': "La date de naissance est requise (vérification d'identité).",
        },
    )

    class Meta:
        model = Recours
        fields = ['source_type', 'source_id', 'date_naissance', 'email', 'message']

    def validate_message(self, message):
        if not (message or '').strip():
            raise serializers.ValidationError("Le message ne peut pas être vide.")
        return message

    def validate(self, data):
        if data['source_type'] == 'dossier':
            obj = (Dossier.objects
                   .exclude(statut=Dossier.Statut.BROUILLON)
                   .filter(pk=data['source_id']).first())
        else:
            obj = ReclamationEligibilite.objects.filter(pk=data['source_id']).first()
        if not obj:
            raise serializers.ValidationError(
                {'source_id': "Enregistrement introuvable. Relancez la recherche."}
            )
        self.context['source_obj'] = obj
        return data

    def create(self, validated_data):
        validated_data.pop('source_type')
        validated_data.pop('source_id')
        obj = self.context['source_obj']
        if isinstance(obj, Dossier):
            validated_data['dossier'] = obj
        else:
            validated_data['reclamation'] = obj
        validated_data['nom'] = obj.nom
        validated_data['postnom'] = obj.postnom
        validated_data['prenom'] = obj.prenom
        return super().create(validated_data)


class RecoursModificationSerializer(serializers.ModelSerializer):
    """Édition d'un recours par le back-office : identité, contact, message et
    date de réception (cree_le, normalement auto)."""

    cree_le = serializers.DateTimeField(required=False)

    class Meta:
        model = Recours
        fields = ['nom', 'postnom', 'prenom', 'date_naissance', 'email',
                  'message', 'cree_le']

    def validate_nom(self, v):
        if not (v or '').strip():
            raise serializers.ValidationError("Le nom est requis.")
        return v.strip()

    def validate_prenom(self, v):
        if not (v or '').strip():
            raise serializers.ValidationError("Le prénom est requis.")
        return v.strip()

    def validate_message(self, v):
        if not (v or '').strip():
            raise serializers.ValidationError("Le message ne peut pas être vide.")
        return v


class RecoursAdminSerializer(serializers.ModelSerializer):
    """Vue back-office d'un recours (avec la source liée)."""

    statut_libelle = serializers.CharField(source='get_statut_display', read_only=True)
    traite_par = serializers.StringRelatedField(read_only=True)
    source = serializers.SerializerMethodField()
    affecte_a = serializers.PrimaryKeyRelatedField(read_only=True)
    affecte_a_nom = serializers.SerializerMethodField()
    # Domaine effectif (correction admin sinon source) + id de la correction.
    poste = serializers.PrimaryKeyRelatedField(read_only=True)
    poste_libelle = serializers.SerializerMethodField()

    class Meta:
        model = Recours
        fields = [
            'id', 'nom', 'postnom', 'prenom', 'date_naissance', 'email', 'message',
            'source', 'poste', 'poste_libelle', 'statut', 'statut_libelle',
            'affecte_a', 'affecte_a_nom', 'reponse', 'traite_par', 'traite_le', 'cree_le',
        ]
        read_only_fields = ['nom', 'postnom', 'prenom', 'date_naissance', 'email',
                            'message', 'cree_le']

    def get_affecte_a_nom(self, obj):
        u = obj.affecte_a
        if not u:
            return ''
        return (u.get_full_name() or u.email)

    def get_poste_libelle(self, obj):
        """Domaine effectif : correction admin (obj.poste) sinon domaine de la
        source (dossier ou réclamation liée)."""
        if obj.poste_id:
            return obj.poste.libelle
        if obj.dossier_id and obj.dossier.poste_id:
            return obj.dossier.poste.libelle
        if obj.reclamation_id and obj.reclamation.poste_id:
            return obj.reclamation.poste.libelle
        return ''

    def get_source(self, obj):
        if obj.dossier_id:
            d = obj.dossier
            return {
                'type': 'dossier', 'id': d.id,
                'appel': d.appel.titre,
                'poste': d.poste.libelle if d.poste else None,
                'statut': d.get_statut_display(),
            }
        if obj.reclamation_id:
            r = obj.reclamation
            return {
                'type': 'reclamation', 'id': r.id,
                'appel': r.appel.titre,
                'poste': r.poste.libelle if r.poste else None,
                'statut': r.get_statut_display(),
            }
        return None
