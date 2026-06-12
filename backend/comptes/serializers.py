from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from candidatures import roles

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Représentation du compte connecté (endpoint « moi »)."""

    prenom = serializers.CharField(source='first_name', required=False, allow_blank=True)
    nom = serializers.CharField(source='last_name', required=False, allow_blank=True)
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'prenom', 'nom', 'email_verifie', 'roles']
        read_only_fields = ['id', 'email', 'email_verifie', 'roles']

    def get_roles(self, obj):
        r = []
        if roles.est_admin(obj):
            r.append('admin')
        if roles.est_validateur(obj):
            r.append('validateur')
        if roles.est_evaluateur(obj):
            r.append('evaluateur')
        if roles.est_correcteur(obj):
            r.append('correcteur')
        if roles.est_lecteur(obj):
            r.append('lecteur')
        if not r:
            r.append('candidat')
        return r


class InscriptionSerializer(serializers.ModelSerializer):
    """Auto-inscription d'un candidat."""

    prenom = serializers.CharField(source='first_name', required=False, allow_blank=True)
    nom = serializers.CharField(source='last_name', required=False, allow_blank=True)
    mot_de_passe = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'prenom', 'nom', 'mot_de_passe']

    def validate_email(self, value):
        value = User.objects.normalize_email(value).lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Un compte existe déjà avec cet email.")
        return value

    def validate_mot_de_passe(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        mot_de_passe = validated_data.pop('mot_de_passe')
        return User.objects.create_user(password=mot_de_passe, **validated_data)


class ConnexionSerializer(serializers.Serializer):
    email = serializers.EmailField()
    mot_de_passe = serializers.CharField(write_only=True)


# Rôles attribuables depuis la page « Utilisateurs » (clé API → groupe Django).
ROLES_ATTRIBUABLES = {
    'admin': roles.GROUPE_ADMIN,
    'validateur': roles.GROUPE_VALIDATEUR,
    'correcteur': roles.GROUPE_CORRECTEUR,
    'lecteur': roles.GROUPE_LECTEUR,
    'evaluateur': roles.GROUPE_EVALUATEUR,
}


class CreationAgentSerializer(serializers.Serializer):
    """Création d'un compte agent (back-office) par un administrateur."""

    email = serializers.EmailField()
    prenom = serializers.CharField(required=False, allow_blank=True, default='')
    nom = serializers.CharField(required=False, allow_blank=True, default='')
    mot_de_passe = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=list(ROLES_ATTRIBUABLES))

    def validate_email(self, value):
        value = User.objects.normalize_email(value).lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "Un compte existe déjà avec cet email. Modifiez son rôle "
                "depuis la liste ci-contre."
            )
        return value

    def validate_mot_de_passe(self, value):
        validate_password(value)
        return value


class ModificationAgentSerializer(serializers.Serializer):
    """Modification d'un compte agent : rôle, actif/inactif, mot de passe."""

    role = serializers.ChoiceField(choices=list(ROLES_ATTRIBUABLES), required=False)
    est_actif = serializers.BooleanField(required=False)
    mot_de_passe = serializers.CharField(write_only=True, required=False)

    def validate_mot_de_passe(self, value):
        validate_password(value)
        return value


class JetonSerializer(serializers.Serializer):
    """Validation d'un jeton seul (vérification email)."""

    jeton = serializers.UUIDField()


class DemandeResetSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ReinitialisationSerializer(serializers.Serializer):
    jeton = serializers.UUIDField()
    nouveau_mot_de_passe = serializers.CharField(write_only=True)

    def validate_nouveau_mot_de_passe(self, value):
        validate_password(value)
        return value
