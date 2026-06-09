"""Admin des comptes — gestion des utilisateurs et de leurs rôles (groupes).

C'est l'un des usages prévus de Django Admin : créer les comptes
Administrateurs / Évaluateurs et les placer dans les bons groupes.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import JetonEmail, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # UserAdmin par défaut suppose un champ username : on reconfigure pour email.
    ordering = ('email',)
    list_display = ('email', 'first_name', 'last_name', 'email_verifie',
                    'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'email_verifie', 'groups')
    search_fields = ('email', 'first_name', 'last_name')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Identité', {'fields': ('first_name', 'last_name')}),
        ('Statut', {'fields': ('email_verifie', 'is_active')}),
        ('Rôles & permissions', {
            'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_staff', 'is_superuser'),
        }),
    )


@admin.register(JetonEmail)
class JetonEmailAdmin(admin.ModelAdmin):
    list_display = ('utilisateur', 'usage', 'cree_le', 'expire_le', 'utilise_le')
    list_filter = ('usage',)
    search_fields = ('utilisateur__email',)
    readonly_fields = ('jeton', 'utilisateur', 'usage', 'cree_le', 'expire_le',
                       'utilise_le')

    def has_add_permission(self, request):
        return False
