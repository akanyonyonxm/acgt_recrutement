<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../../api'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const snack = ref({ show: false, color: 'success', text: '' })
const notifier = (text, color = 'success') => (snack.value = { show: true, color, text })

// Rôles attribuables, avec libellé et description (alignés sur le backend).
const ROLES = [
  { value: 'lecteur', titre: 'Lecteur', couleur: 'blue-grey',
    description: 'Consulte tout (dossiers, réclamations, pièces) — aucune action.' },
  { value: 'validateur', titre: 'Validateur', couleur: 'teal',
    description: 'Traite les dossiers et réclamations : approuver, rejeter, retenir… Ne modifie pas les informations.' },
  { value: 'correcteur', titre: 'Correcteur', couleur: 'indigo',
    description: 'Corrige les identités (code, nom, postnom, prénom) — ne valide pas.' },
  { value: 'evaluateur', titre: 'Évaluateur', couleur: 'deep-purple',
    description: 'Examine les dossiers où il est désigné (espace évaluateur).' },
  { value: 'admin', titre: 'Administrateur', couleur: 'primary',
    description: 'Accès complet : validation, modifications, import, publication, utilisateurs.' },
]
const ROLE_PAR_CLE = Object.fromEntries(ROLES.map((r) => [r.value, r]))
function libelleRole(cle) { return ROLE_PAR_CLE[cle]?.titre || cle }
function couleurRole(cle) { return ROLE_PAR_CLE[cle]?.couleur || 'grey' }

// --- Liste -----------------------------------------------------------
const agents = ref([])
const loading = ref(false)
const ENTETES = [
  { title: 'Agent', key: 'nom_complet', sortable: false },
  { title: 'Email', key: 'email' },
  { title: 'Rôle', key: 'roles', sortable: false },
  { title: 'Actif', key: 'est_actif', align: 'center' },
  { title: 'Dernière connexion', key: 'derniere_connexion' },
  { title: '', key: 'actions', sortable: false, align: 'end' },
]

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
  if (!d) return 'Jamais'
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
  <div>
    <div class="d-flex align-center mb-5">
      <v-icon color="primary" size="30" class="mr-3">mdi-account-cog-outline</v-icon>
      <h1 class="text-h5 font-weight-bold text-primary">Utilisateurs &amp; accès</h1>
      <v-spacer />
      <v-btn color="primary" variant="flat" prepend-icon="mdi-account-plus" @click="ouvrirCreation">
        Donner un accès
      </v-btn>
    </div>

    <!-- Rappel des profils -->
    <v-row dense class="mb-5">
      <v-col v-for="r in ROLES" :key="r.value" cols="12" sm="6" md="4">
        <v-card flat border class="pa-3 h-100">
          <v-chip :color="couleurRole(r.value)" size="small" variant="flat" class="mb-2 font-weight-bold">
            {{ r.titre }}
          </v-chip>
          <div class="text-caption text-medium-emphasis">{{ r.description }}</div>
        </v-card>
      </v-col>
    </v-row>

    <v-card flat border>
      <v-data-table
        :headers="ENTETES"
        :items="agents"
        :loading="loading"
        :items-per-page="25"
        no-data-text="Aucun compte agent."
        class="tableau-admin"
      >
        <template #item.nom_complet="{ item }">
          <span class="font-weight-bold text-primary">
            {{ `${item.prenom} ${item.nom}`.trim() || '—' }}
          </span>
          <v-chip v-if="item.est_superuser" size="x-small" color="secondary" variant="flat" class="ml-2">
            superuser
          </v-chip>
          <v-chip v-if="item.id === auth.utilisateur?.id" size="x-small" color="accent" variant="flat" class="ml-2">
            vous
          </v-chip>
        </template>
        <template #item.roles="{ item }">
          <v-chip v-for="r in item.roles" :key="r" :color="couleurRole(r)" size="small"
                  variant="tonal" class="mr-1 font-weight-bold">
            {{ libelleRole(r) }}
          </v-chip>
        </template>
        <template #item.est_actif="{ item }">
          <v-icon :color="item.est_actif ? 'success' : 'error'" size="small">
            {{ item.est_actif ? 'mdi-check-circle' : 'mdi-cancel' }}
          </v-icon>
        </template>
        <template #item.derniere_connexion="{ item }">
          <span class="text-caption">{{ formaterDate(item.derniere_connexion) }}</span>
        </template>
        <template #item.actions="{ item }">
          <template v-if="modifiable(item)">
            <v-tooltip text="Modifier le rôle / mot de passe" location="top">
              <template #activator="{ props }">
                <v-btn v-bind="props" icon="mdi-pencil" variant="text" size="small"
                       color="primary" @click="ouvrirEdition(item)" />
              </template>
            </v-tooltip>
            <v-tooltip :text="item.est_actif ? 'Désactiver (bloquer la connexion)' : 'Réactiver'" location="top">
              <template #activator="{ props }">
                <v-btn v-bind="props" :icon="item.est_actif ? 'mdi-account-off' : 'mdi-account-check'"
                       variant="text" size="small" :color="item.est_actif ? 'error' : 'success'"
                       @click="basculerActif(item)" />
              </template>
            </v-tooltip>
          </template>
        </template>
      </v-data-table>
    </v-card>

    <!-- Dialog création -->
    <v-dialog v-model="dialogCreer" max-width="560">
      <v-card>
        <v-card-title class="d-flex align-center bg-primary text-white">
          <v-icon class="mr-2">mdi-account-plus</v-icon>Donner un accès
        </v-card-title>
        <v-card-text class="pt-4">
          <v-row dense>
            <v-col cols="12" sm="6"><v-text-field v-model="formCreer.prenom" label="Prénom" /></v-col>
            <v-col cols="12" sm="6"><v-text-field v-model="formCreer.nom" label="Nom" /></v-col>
            <v-col cols="12">
              <v-text-field v-model="formCreer.email" label="Email *" type="email"
                            prepend-inner-icon="mdi-email-outline" />
            </v-col>
            <v-col cols="12">
              <v-text-field v-model="formCreer.mot_de_passe" label="Mot de passe *"
                            :type="voirMdp ? 'text' : 'password'"
                            :append-inner-icon="voirMdp ? 'mdi-eye-off' : 'mdi-eye'"
                            @click:append-inner="voirMdp = !voirMdp"
                            hint="Au moins 8 caractères, pas trop simple." persistent-hint />
            </v-col>
            <v-col cols="12">
              <v-select v-model="formCreer.role" :items="ROLES" item-title="titre" item-value="value"
                        label="Profil d'accès *" />
              <v-alert type="info" variant="tonal" density="compact">{{ descriptionRoleCreer }}</v-alert>
            </v-col>
          </v-row>
        </v-card-text>
        <v-card-actions class="pa-4 pt-0">
          <span class="text-caption text-medium-emphasis">* obligatoire</span>
          <v-spacer />
          <v-btn variant="text" @click="dialogCreer = false">Annuler</v-btn>
          <v-btn color="primary" variant="flat" :loading="enCreation" @click="creer">Créer le compte</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Dialog modification -->
    <v-dialog v-model="dialogEdit" max-width="560">
      <v-card v-if="agentEdit">
        <v-card-title class="d-flex align-center bg-primary text-white">
          <v-icon class="mr-2">mdi-account-edit</v-icon>{{ agentEdit.email }}
        </v-card-title>
        <v-card-text class="pt-4">
          <v-select v-model="formEdit.role" :items="ROLES" item-title="titre" item-value="value"
                    label="Profil d'accès" />
          <v-alert type="info" variant="tonal" density="compact" class="mb-4">{{ descriptionRoleEdit }}</v-alert>
          <v-text-field v-model="formEdit.mot_de_passe" label="Nouveau mot de passe (laisser vide pour ne pas changer)"
                        :type="voirMdpEdit ? 'text' : 'password'"
                        :append-inner-icon="voirMdpEdit ? 'mdi-eye-off' : 'mdi-eye'"
                        @click:append-inner="voirMdpEdit = !voirMdpEdit" />
        </v-card-text>
        <v-card-actions class="pa-4 pt-0">
          <v-spacer />
          <v-btn variant="text" @click="dialogEdit = false">Annuler</v-btn>
          <v-btn color="primary" variant="flat" :loading="enEdit" @click="enregistrerEdition">Enregistrer</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snack.show" :color="snack.color" timeout="4000">{{ snack.text }}</v-snackbar>
  </div>
</template>

<style scoped>
.tableau-admin :deep(thead th) { background: #f4f5f9; font-weight: 700 !important; color: #1a237e !important; text-transform: uppercase; font-size: 0.72rem; letter-spacing: 0.03em; }
</style>
