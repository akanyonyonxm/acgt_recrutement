<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../../api'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const snack = ref({ show: false, color: 'success', text: '' })
const notifier = (text, color = 'success') => (snack.value = { show: true, color, text })

// Rôles attribuables : libellé, couleur Vuetify (chips), hex (badges/accents),
// icône MDI et description. Alignés sur le backend.
const ROLES = [
  { value: 'lecteur', titre: 'Lecteur', couleur: 'blue-grey', hex: '#546E7A',
    icone: 'mdi-eye-outline',
    description: 'Consulte tout (dossiers, réclamations, pièces) — aucune action.' },
  { value: 'validateur', titre: 'Validateur', couleur: 'teal', hex: '#00897B',
    icone: 'mdi-check-decagram-outline',
    description: 'Traite les dossiers et réclamations : approuver, rejeter, retenir… Ne modifie pas les informations.' },
  { value: 'correcteur', titre: 'Correcteur', couleur: 'indigo', hex: '#3949AB',
    icone: 'mdi-pencil-outline',
    description: 'Corrige les identités (code, nom, postnom, prénom) — ne valide pas.' },
  { value: 'evaluateur', titre: 'Évaluateur', couleur: 'deep-purple', hex: '#5E35B1',
    icone: 'mdi-clipboard-text-search-outline',
    description: 'Examine les dossiers où il est désigné (espace évaluateur).' },
  { value: 'superviseur', titre: 'Supervision', couleur: 'deep-orange', hex: '#E65100',
    icone: 'mdi-shield-star-outline',
    description: 'Accès à tout sauf l’administration : traite, répartit la charge, publie les retenus, désigne les évaluateurs. Ne gère pas les comptes, n’importe pas la liste, ne modifie pas les noms/codes.' },
  { value: 'admin', titre: 'Administrateur', couleur: 'primary', hex: '#1a237e',
    icone: 'mdi-shield-crown-outline',
    description: 'Accès complet : validation, modifications (noms/codes), import, publication, comptes utilisateurs.' },
]
const ROLE_PAR_CLE = Object.fromEntries(ROLES.map((r) => [r.value, r]))
// Ordre d'importance pour choisir le rôle « principal » (couleur de l'avatar).
const PRIORITE = ['admin', 'superviseur', 'validateur', 'correcteur', 'evaluateur', 'lecteur']
function libelleRole(cle) { return ROLE_PAR_CLE[cle]?.titre || cle }
function couleurRole(cle) { return ROLE_PAR_CLE[cle]?.couleur || 'grey' }
function hexRole(cle) { return ROLE_PAR_CLE[cle]?.hex || '#90A4AE' }

function rolePrincipal(item) {
  const cle = PRIORITE.find((p) => item.roles.includes(p))
  return cle || (item.roles[0] || 'lecteur')
}
function initiales(item) {
  const p = (item.prenom || '').trim(), n = (item.nom || '').trim()
  if (p || n) return ((p[0] || '') + (n[0] || '')).toUpperCase()
  return ((item.email || '?')[0] || '?').toUpperCase()
}

// --- Liste -----------------------------------------------------------
const agents = ref([])
const loading = ref(false)
const ENTETES = [
  { title: 'Agent', key: 'nom_complet', sortable: false },
  { title: 'Rôle', key: 'roles', sortable: false },
  { title: 'Statut', key: 'est_actif', align: 'center' },
  { title: 'Dernière connexion', key: 'derniere_connexion' },
  { title: '', key: 'actions', sortable: false, align: 'end' },
]

const nbActifs = computed(() => agents.value.filter((a) => a.est_actif).length)

async function charger() {
  loading.value = true
  try {
    const { data } = await api.get('/auth/utilisateurs/')
    agents.value = data
  } catch (e) {
    notifier(e.response?.data?.detail || 'Chargement impossible.', 'error')
  } finally {
    loading.value = false
  }
}

function formaterDate(d) {
  if (!d) return null
  return new Date(d).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
}

// Un compte est modifiable s'il n'est ni superuser ni soi-même (garde-fous serveur).
function modifiable(item) {
  return !item.est_superuser && item.id !== auth.utilisateur?.id
}

// --- Création --------------------------------------------------------
const dialogCreer = ref(false)
const formCreer = ref({ email: '', prenom: '', nom: '', mot_de_passe: '', role: 'lecteur' })
const enCreation = ref(false)
const voirMdp = ref(false)

function ouvrirCreation() {
  formCreer.value = { email: '', prenom: '', nom: '', mot_de_passe: '', role: 'lecteur' }
  voirMdp.value = false
  dialogCreer.value = true
}

async function creer() {
  if (!formCreer.value.email.trim()) return notifier("L'email est obligatoire.", 'error')
  if (!formCreer.value.mot_de_passe) return notifier('Le mot de passe est obligatoire.', 'error')
  enCreation.value = true
  try {
    await api.post('/auth/utilisateurs/', formCreer.value)
    dialogCreer.value = false
    notifier('Compte créé. Communiquez l’email et le mot de passe à la personne.')
    await charger()
  } catch (e) {
    const d = e.response?.data
    notifier(d?.email?.[0] || d?.mot_de_passe?.[0] || d?.detail || 'Création impossible.', 'error')
  } finally {
    enCreation.value = false
  }
}

// --- Modification (rôle / actif / mot de passe) ----------------------
const dialogEdit = ref(false)
const agentEdit = ref(null)
const formEdit = ref({ role: '', mot_de_passe: '' })
const enEdit = ref(false)
const voirMdpEdit = ref(false)

function ouvrirEdition(item) {
  agentEdit.value = item
  // Premier rôle attribuable trouvé sur le compte (un seul rôle à la fois).
  const role = ROLES.map((r) => r.value).find((r) => item.roles.includes(r)) || 'lecteur'
  formEdit.value = { role, mot_de_passe: '' }
  voirMdpEdit.value = false
  dialogEdit.value = true
}

async function enregistrerEdition() {
  enEdit.value = true
  try {
    const corps = { role: formEdit.value.role }
    if (formEdit.value.mot_de_passe) corps.mot_de_passe = formEdit.value.mot_de_passe
    await api.patch(`/auth/utilisateurs/${agentEdit.value.id}/`, corps)
    dialogEdit.value = false
    notifier('Compte mis à jour.')
    await charger()
  } catch (e) {
    const d = e.response?.data
    notifier(d?.mot_de_passe?.[0] || d?.detail || 'Modification impossible.', 'error')
  } finally {
    enEdit.value = false
  }
}

async function basculerActif(item) {
  try {
    await api.patch(`/auth/utilisateurs/${item.id}/`, { est_actif: !item.est_actif })
    notifier(item.est_actif ? 'Compte désactivé (connexion bloquée).' : 'Compte réactivé.')
    await charger()
  } catch (e) {
    notifier(e.response?.data?.detail || 'Opération impossible.', 'error')
  }
}

const descriptionRoleCreer = computed(() => ROLE_PAR_CLE[formCreer.value.role]?.description || '')
const descriptionRoleEdit = computed(() => ROLE_PAR_CLE[formEdit.value.role]?.description || '')

onMounted(charger)
</script>

<template>
  <div class="page-utilisateurs">
    <!-- En-tête -->
    <div class="entete">
      <div class="entete-titre">
        <div class="entete-badge"><v-icon size="26">mdi-account-cog-outline</v-icon></div>
        <div>
          <h1 class="titre">Utilisateurs &amp; accès</h1>
          <p class="sous-titre">
            Gérez qui accède à l'espace de traitement et avec quel niveau de droits.
          </p>
        </div>
      </div>
      <div class="entete-droite">
        <div class="compteur">
          <span class="compteur-val">{{ agents.length }}</span>
          <span class="compteur-lib">compte(s)<template v-if="agents.length"> · {{ nbActifs }} actif(s)</template></span>
        </div>
        <v-btn color="primary" variant="flat" size="large" rounded="lg" class="font-weight-bold"
               prepend-icon="mdi-account-plus" @click="ouvrirCreation">
          Donner un accès
        </v-btn>
      </div>
    </div>

    <!-- Légende des profils -->
    <div class="section-label">Les profils d'accès</div>
    <div class="roles-grid mb-8">
      <div v-for="r in ROLES" :key="r.value" class="role-carte" :style="{ '--accent': r.hex }">
        <div class="role-haut">
          <span class="role-ic"><v-icon size="20">{{ r.icone }}</v-icon></span>
          <span class="role-titre">{{ r.titre }}</span>
        </div>
        <p class="role-desc">{{ r.description }}</p>
      </div>
    </div>

    <!-- Tableau des agents -->
    <v-card class="carte-tableau" elevation="0">
      <v-data-table
        :headers="ENTETES"
        :items="agents"
        :loading="loading"
        :items-per-page="25"
        no-data-text="Aucun compte agent pour le moment."
        class="tableau-admin"
      >
        <template #item.nom_complet="{ item }">
          <div class="agent-cell">
            <v-avatar size="40" :style="{ background: hexRole(rolePrincipal(item)) }" class="agent-avatar">
              <span>{{ initiales(item) }}</span>
            </v-avatar>
            <div class="agent-infos">
              <div class="agent-nom">
                {{ `${item.prenom} ${item.nom}`.trim() || '—' }}
                <v-chip v-if="item.est_superuser" size="x-small" variant="flat" class="tag-su">superuser</v-chip>
                <v-chip v-if="item.id === auth.utilisateur?.id" size="x-small" color="accent"
                        variant="flat" class="tag-vous">vous</v-chip>
              </div>
              <div class="agent-mail">{{ item.email }}</div>
            </div>
          </div>
        </template>

        <template #item.roles="{ item }">
          <div class="d-flex flex-wrap ga-1 py-1">
            <v-chip v-for="r in item.roles" :key="r" :color="couleurRole(r)" size="small"
                    variant="tonal" class="font-weight-bold" :prepend-icon="ROLE_PAR_CLE[r]?.icone">
              {{ libelleRole(r) }}
            </v-chip>
          </div>
        </template>

        <template #item.est_actif="{ item }">
          <span class="statut-pill" :class="item.est_actif ? 'on' : 'off'">
            <span class="dot" /> {{ item.est_actif ? 'Actif' : 'Inactif' }}
          </span>
        </template>

        <template #item.derniere_connexion="{ item }">
          <span v-if="formaterDate(item.derniere_connexion)" class="date-conn">
            {{ formaterDate(item.derniere_connexion) }}
          </span>
          <span v-else class="date-jamais">Jamais connecté</span>
        </template>

        <template #item.actions="{ item }">
          <div class="actions-cell">
            <template v-if="modifiable(item)">
              <v-tooltip text="Modifier le rôle / mot de passe" location="top">
                <template #activator="{ props }">
                  <v-btn v-bind="props" icon="mdi-pencil-outline" variant="text" size="small"
                         color="primary" @click="ouvrirEdition(item)" />
                </template>
              </v-tooltip>
              <v-tooltip :text="item.est_actif ? 'Désactiver (bloquer la connexion)' : 'Réactiver'" location="top">
                <template #activator="{ props }">
                  <v-btn v-bind="props" :icon="item.est_actif ? 'mdi-account-off-outline' : 'mdi-account-check-outline'"
                         variant="text" size="small" :color="item.est_actif ? 'error' : 'success'"
                         @click="basculerActif(item)" />
                </template>
              </v-tooltip>
            </template>
            <v-icon v-else color="grey-lighten-1" size="small" class="mr-2">mdi-lock-outline</v-icon>
          </div>
        </template>
      </v-data-table>
    </v-card>

    <!-- Dialog création -->
    <v-dialog v-model="dialogCreer" max-width="560">
      <v-card rounded="xl">
        <v-card-title class="dialog-titre">
          <v-icon class="mr-2">mdi-account-plus</v-icon>Donner un accès
        </v-card-title>
        <v-card-text class="pt-5">
          <v-row dense>
            <v-col cols="12" sm="6"><v-text-field v-model="formCreer.prenom" label="Prénom" variant="outlined" density="comfortable" /></v-col>
            <v-col cols="12" sm="6"><v-text-field v-model="formCreer.nom" label="Nom" variant="outlined" density="comfortable" /></v-col>
            <v-col cols="12">
              <v-text-field v-model="formCreer.email" label="Email *" type="email" variant="outlined" density="comfortable"
                            prepend-inner-icon="mdi-email-outline" />
            </v-col>
            <v-col cols="12">
              <v-text-field v-model="formCreer.mot_de_passe" label="Mot de passe *" variant="outlined" density="comfortable"
                            :type="voirMdp ? 'text' : 'password'" prepend-inner-icon="mdi-lock-outline"
                            :append-inner-icon="voirMdp ? 'mdi-eye-off' : 'mdi-eye'"
                            @click:append-inner="voirMdp = !voirMdp"
                            hint="Au moins 8 caractères, pas trop simple." persistent-hint />
            </v-col>
            <v-col cols="12">
              <v-select v-model="formCreer.role" :items="ROLES" item-title="titre" item-value="value"
                        label="Profil d'accès *" variant="outlined" density="comfortable"
                        prepend-inner-icon="mdi-shield-account-outline" />
              <v-alert type="info" variant="tonal" density="compact" class="mt-1">{{ descriptionRoleCreer }}</v-alert>
            </v-col>
          </v-row>
        </v-card-text>
        <v-card-actions class="pa-4 pt-0">
          <span class="text-caption text-medium-emphasis">* obligatoire</span>
          <v-spacer />
          <v-btn variant="text" @click="dialogCreer = false">Annuler</v-btn>
          <v-btn color="primary" variant="flat" rounded="lg" :loading="enCreation" @click="creer">Créer le compte</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Dialog modification -->
    <v-dialog v-model="dialogEdit" max-width="560">
      <v-card v-if="agentEdit" rounded="xl">
        <v-card-title class="dialog-titre">
          <v-icon class="mr-2">mdi-account-edit</v-icon>{{ agentEdit.email }}
        </v-card-title>
        <v-card-text class="pt-5">
          <v-select v-model="formEdit.role" :items="ROLES" item-title="titre" item-value="value"
                    label="Profil d'accès" variant="outlined" density="comfortable"
                    prepend-inner-icon="mdi-shield-account-outline" />
          <v-alert type="info" variant="tonal" density="compact" class="mb-4">{{ descriptionRoleEdit }}</v-alert>
          <v-text-field v-model="formEdit.mot_de_passe" variant="outlined" density="comfortable"
                        label="Nouveau mot de passe (laisser vide pour ne pas changer)"
                        :type="voirMdpEdit ? 'text' : 'password'" prepend-inner-icon="mdi-lock-reset"
                        :append-inner-icon="voirMdpEdit ? 'mdi-eye-off' : 'mdi-eye'"
                        @click:append-inner="voirMdpEdit = !voirMdpEdit" />
        </v-card-text>
        <v-card-actions class="pa-4 pt-0">
          <v-spacer />
          <v-btn variant="text" @click="dialogEdit = false">Annuler</v-btn>
          <v-btn color="primary" variant="flat" rounded="lg" :loading="enEdit" @click="enregistrerEdition">Enregistrer</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snack.show" :color="snack.color" timeout="4000">{{ snack.text }}</v-snackbar>
  </div>
</template>

<style scoped>
.page-utilisateurs { max-width: 1280px; }

/* --- En-tête --- */
.entete { display: flex; align-items: flex-start; justify-content: space-between;
  flex-wrap: wrap; gap: 20px; margin-bottom: 36px; }
.entete-titre { display: flex; align-items: center; gap: 16px; }
.entete-badge { width: 52px; height: 52px; border-radius: 16px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center; color: #fff;
  background: linear-gradient(135deg, #1a237e 0%, #3949AB 100%);
  box-shadow: 0 8px 20px rgba(26, 35, 126, 0.28); }
.titre { font-size: 1.6rem; font-weight: 800; color: #1a237e; line-height: 1.1; letter-spacing: -0.3px; }
.sous-titre { font-size: 0.9rem; color: #6b7280; margin: 4px 0 0; max-width: 460px; }
.entete-droite { display: flex; align-items: center; gap: 20px; }
.compteur { text-align: right; line-height: 1.1; }
.compteur-val { display: block; font-size: 1.5rem; font-weight: 800; color: #1a237e; }
.compteur-lib { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.04em; color: #9098a8; }

/* --- Légende des profils --- */
.section-label { font-size: 0.72rem; font-weight: 800; letter-spacing: 0.08em;
  text-transform: uppercase; color: #9098a8; margin-bottom: 14px; }
.roles-grid { display: grid; gap: 16px;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }
.role-carte { position: relative; background: #fff; border: 1px solid #e9ebf2;
  border-radius: 16px; padding: 18px 18px 18px 22px; overflow: hidden;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease; }
.role-carte::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0;
  width: 4px; background: var(--accent); }
.role-carte:hover { transform: translateY(-3px); border-color: color-mix(in srgb, var(--accent) 40%, #e9ebf2);
  box-shadow: 0 12px 26px rgba(26, 35, 126, 0.1); }
.role-haut { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.role-ic { width: 34px; height: 34px; border-radius: 10px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center; color: var(--accent);
  background: color-mix(in srgb, var(--accent) 12%, #fff); }
.role-titre { font-size: 0.98rem; font-weight: 800; color: #1f2430; }
.role-desc { font-size: 0.8rem; line-height: 1.5; color: #6b7280; margin: 0; }

/* --- Tableau --- */
.carte-tableau { border: 1px solid #e9ebf2; border-radius: 18px; overflow: hidden;
  box-shadow: 0 6px 24px rgba(26, 35, 126, 0.06); }
.tableau-admin :deep(thead th) { background: #f6f7fb !important; font-weight: 700 !important;
  color: #1a237e !important; text-transform: uppercase; font-size: 0.7rem; letter-spacing: 0.05em;
  height: 52px; }
.tableau-admin :deep(tbody td) { padding-top: 14px !important; padding-bottom: 14px !important;
  border-bottom: 1px solid #f0f1f6 !important; }
.tableau-admin :deep(tbody tr) { transition: background 0.12s ease; }
.tableau-admin :deep(tbody tr:hover) { background: #fafbff !important; }

.agent-cell { display: flex; align-items: center; gap: 14px; }
.agent-avatar { color: #fff; font-weight: 800; font-size: 0.86rem; letter-spacing: 0.5px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.14); }
.agent-infos { min-width: 0; }
.agent-nom { font-weight: 700; color: #1f2430; font-size: 0.94rem; display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.agent-mail { font-size: 0.8rem; color: #8a92a4; margin-top: 1px; }
.tag-su { background: #0d1b2a !important; color: #fff !important; font-weight: 700; }
.tag-vous { font-weight: 700; }

/* Pastille de statut */
.statut-pill { display: inline-flex; align-items: center; gap: 7px; padding: 4px 12px;
  border-radius: 9999px; font-size: 0.76rem; font-weight: 700; }
.statut-pill .dot { width: 7px; height: 7px; border-radius: 50%; }
.statut-pill.on { background: rgba(46, 125, 50, 0.1); color: #2E7D32; }
.statut-pill.on .dot { background: #2E7D32; box-shadow: 0 0 0 3px rgba(46, 125, 50, 0.16); }
.statut-pill.off { background: rgba(198, 40, 40, 0.09); color: #C62828; }
.statut-pill.off .dot { background: #C62828; }

.date-conn { font-size: 0.82rem; color: #5b6373; }
.date-jamais { font-size: 0.8rem; color: #b0b7c3; font-style: italic; }
.actions-cell { display: flex; align-items: center; justify-content: flex-end; gap: 2px; }

/* --- Dialogs --- */
.dialog-titre { display: flex; align-items: center; padding: 18px 24px;
  background: linear-gradient(135deg, #1a237e 0%, #283593 100%); color: #fff;
  font-size: 1.05rem; font-weight: 700; }
</style>
