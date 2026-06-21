<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../../api'
import { useAuthStore } from '../../stores/auth'
import StatCard from '../../components/StatCard.vue'

const auth = useAuthStore()
const STORAGE_FILTRES = `acgt_filtres_recours_${auth.utilisateur?.id ?? 'anon'}`
const sauve = JSON.parse(localStorage.getItem(STORAGE_FILTRES) || '{}')

const recours = ref([])
const total = ref(0)
const chargement = ref(false)
const stats = ref({ total: 0, en_attente: 0, traite: 0 })

const statut = ref(sauve.statut ?? '')
const q = ref(sauve.q ?? '')
const tri = ref(Array.isArray(sauve.tri) ? sauve.tri : [])

const detail = ref(null)
const dialog = ref(false)
const reponse = ref('')
const enAction = ref(false)
const snack = ref({ show: false, color: 'success', text: '' })

const notifier = (text, color = 'success') => (snack.value = { show: true, color, text })
const dateFr = (d) => (d ? new Date(d).toLocaleDateString('fr-FR') : '—')
const COULEUR_STATUT = { en_attente: 'warning', traite: 'success' }

const headers = [
  { title: 'Personne', key: 'nom' },
  { title: 'Né(e) le', key: 'date_naissance', sortable: false },
  { title: 'Email', key: 'email', sortable: false },
  { title: 'Lié à', key: 'source', sortable: false },
  { title: 'Message', key: 'message', sortable: false },
  { title: 'Statut', key: 'statut' },
  { title: 'Reçu le', key: 'cree_le' },
  { title: '', key: 'actions', sortable: false, align: 'end' },
]
const TRI = { nom: 'nom', statut: 'statut', cree_le: 'cree_le' }

const cle = computed(() => `${statut.value}|${q.value}`)

function memoriser() {
  localStorage.setItem(STORAGE_FILTRES, JSON.stringify({
    statut: statut.value, q: q.value, tri: tri.value,
  }))
}

async function chargerStats() {
  const { data } = await api.get('/recours/stats/')
  stats.value = data
}

async function charger({ page = 1, itemsPerPage = 25, sortBy } = {}) {
  chargement.value = true
  try {
    if (sortBy !== undefined) tri.value = sortBy
    const params = { page, page_size: itemsPerPage > 0 ? itemsPerPage : 25 }
    if (statut.value) params.statut = statut.value
    if (q.value) params.q = q.value
    const s = tri.value && tri.value[0]
    if (s && TRI[s.key]) params.ordering = (s.order === 'desc' ? '-' : '') + TRI[s.key]
    const { data } = await api.get('/recours/', { params })
    recours.value = data.results
    total.value = data.count
    memoriser()
    chargerStats()
  } finally {
    chargement.value = false
  }
}

function filtrerStatut(s) { statut.value = statut.value === s ? '' : s }

function ouvrir(r) {
  detail.value = r
  reponse.value = r.reponse || ''
  modeEdition.value = false
  dialog.value = true
}

async function traiter() {
  enAction.value = true
  try {
    const { data } = await api.post(`/recours/${detail.value.id}/traiter/`, { reponse: reponse.value })
    Object.assign(detail.value, data)
    notifier('Recours marqué comme traité.')
    dialog.value = false
    charger()
  } catch (e) {
    notifier(e.response?.data?.detail || 'Action impossible.', 'error')
  } finally {
    enAction.value = false
  }
}

async function rouvrir() {
  enAction.value = true
  try {
    const { data } = await api.post(`/recours/${detail.value.id}/rouvrir/`)
    Object.assign(detail.value, data)
    notifier('Recours rouvert (en attente).')
    dialog.value = false
    charger()
  } catch (e) {
    notifier(e.response?.data?.detail || 'Action impossible.', 'error')
  } finally {
    enAction.value = false
  }
}

const nomComplet = (r) => [r.nom, r.postnom, r.prenom].filter(Boolean).join(' ')

// --- Édition d'un recours (identité, contact, message, date de réception) ---
const modeEdition = ref(false)
const edit = ref({})

function ouvrirEdition() {
  edit.value = {
    nom: detail.value.nom, postnom: detail.value.postnom, prenom: detail.value.prenom,
    date_naissance: detail.value.date_naissance,
    email: detail.value.email, message: detail.value.message,
    cree_le: (detail.value.cree_le || '').slice(0, 10),   // YYYY-MM-DD
  }
  modeEdition.value = true
}

async function enregistrer() {
  enAction.value = true
  try {
    const { data } = await api.patch(`/recours/${detail.value.id}/`, edit.value)
    Object.assign(detail.value, data)
    notifier('Recours modifié.')
    modeEdition.value = false
    charger()
  } catch (e) {
    const d = e.response?.data
    notifier(d?.detail || d?.nom?.[0] || d?.prenom?.[0] || d?.message?.[0]
      || d?.cree_le?.[0] || 'Modification impossible.', 'error')
  } finally {
    enAction.value = false
  }
}

onMounted(() => {})
</script>

<template>
  <div>
    <div class="d-flex align-center flex-wrap ga-3 mb-5">
      <v-icon color="primary" size="32">mdi-gavel</v-icon>
      <h1 class="text-h5 font-weight-bold text-primary mb-0">Recours</h1>
      <v-spacer />
      <v-text-field v-model="q" placeholder="Rechercher (nom, email)…"
                    density="compact" variant="outlined" hide-details prepend-inner-icon="mdi-magnify"
                    style="max-width: 280px" clearable />
    </div>

    <!-- KPI -->
    <v-row dense class="mb-4">
      <v-col cols="12" sm="4">
        <StatCard icon="mdi-gavel" :value="stats.total" label="Total recours"
                  description="Tous statuts" color="#5E35B1"
                  clickable :active="statut === ''" @click="filtrerStatut('')" />
      </v-col>
      <v-col cols="12" sm="4">
        <StatCard icon="mdi-clock-outline" :value="stats.en_attente" label="En attente"
                  description="À examiner" color="#EF6C00"
                  clickable :active="statut === 'en_attente'" @click="filtrerStatut('en_attente')" />
      </v-col>
      <v-col cols="12" sm="4">
        <StatCard icon="mdi-check-circle-outline" :value="stats.traite" label="Traités"
                  description="Examinés" color="#2E7D32"
                  clickable :active="statut === 'traite'" @click="filtrerStatut('traite')" />
      </v-col>
    </v-row>

    <v-card flat border rounded="lg">
      <v-data-table-server
        :headers="headers" :items="recours" :items-length="total" :loading="chargement"
        :items-per-page="25" :items-per-page-options="[25, 50, 100]"
        :sort-by="tri" :search="cle" @update:options="charger">
        <template #[`item.nom`]="{ item }">
          <span class="font-weight-medium">{{ item.nom }}</span>
          <span class="text-medium-emphasis"> {{ item.postnom }} {{ item.prenom }}</span>
        </template>
        <template #[`item.date_naissance`]="{ item }">{{ dateFr(item.date_naissance) }}</template>
        <template #[`item.email`]="{ item }">{{ item.email || '—' }}</template>
        <template #[`item.source`]="{ item }">
          <v-chip v-if="item.source" size="x-small"
                  :color="item.source.type === 'reclamation' ? '#00838F' : 'primary'" variant="tonal">
            {{ item.source.type === 'reclamation' ? 'Réclamation' : 'Dossier' }} #{{ item.source.id }}
          </v-chip>
          <span v-else class="text-medium-emphasis">—</span>
        </template>
        <template #[`item.message`]="{ item }">
          <span class="message-court">{{ item.message }}</span>
        </template>
        <template #[`item.statut`]="{ item }">
          <v-chip :color="COULEUR_STATUT[item.statut]" size="small" variant="flat">
            {{ item.statut_libelle }}
          </v-chip>
        </template>
        <template #[`item.cree_le`]="{ item }">{{ dateFr(item.cree_le) }}</template>
        <template #[`item.actions`]="{ item }">
          <v-btn variant="text" color="primary" size="small" append-icon="mdi-arrow-right"
                 @click="ouvrir(item)">Examiner</v-btn>
        </template>
        <template #no-data>
          <div class="text-center py-8 text-medium-emphasis">Aucun recours.</div>
        </template>
      </v-data-table-server>
    </v-card>

    <!-- Détail / traitement -->
    <v-dialog v-model="dialog" max-width="640">
      <v-card v-if="detail" rounded="lg">
        <v-card-title class="d-flex align-center ga-2 pa-4">
          <span class="text-h6">{{ nomComplet(detail) }}</span>
          <v-spacer />
          <v-chip :color="COULEUR_STATUT[detail.statut]" size="small" variant="flat">{{ detail.statut_libelle }}</v-chip>
        </v-card-title>
        <v-divider />
        <v-card-text class="pa-4">
          <!-- Mode ÉDITION -->
          <template v-if="modeEdition">
            <v-row dense>
              <v-col cols="12" sm="4"><v-text-field v-model="edit.nom" label="Nom *" density="compact" variant="outlined" hide-details /></v-col>
              <v-col cols="12" sm="4"><v-text-field v-model="edit.postnom" label="Postnom" density="compact" variant="outlined" hide-details /></v-col>
              <v-col cols="12" sm="4"><v-text-field v-model="edit.prenom" label="Prénom *" density="compact" variant="outlined" hide-details /></v-col>
            </v-row>
            <v-row dense class="mt-1">
              <v-col cols="12" sm="4"><v-text-field v-model="edit.date_naissance" label="Date de naissance" type="date" density="compact" variant="outlined" hide-details /></v-col>
              <v-col cols="12" sm="4"><v-text-field v-model="edit.cree_le" label="Date de réception" type="date" density="compact" variant="outlined" hide-details /></v-col>
              <v-col cols="12" sm="4"><v-text-field v-model="edit.email" label="Email" type="email" density="compact" variant="outlined" hide-details /></v-col>
            </v-row>
            <v-textarea v-model="edit.message" label="Message" rows="4" variant="outlined" hide-details class="mt-2" />
          </template>

          <!-- Mode LECTURE -->
          <template v-else>
            <div class="d-flex ga-4 mb-3 text-body-2 flex-wrap">
              <span class="dn"><v-icon size="16">mdi-cake-variant-outline</v-icon> Né(e) le {{ dateFr(detail.date_naissance) }}</span>
              <span v-if="detail.email"><v-icon size="16">mdi-email-outline</v-icon> {{ detail.email }}</span>
              <span class="text-medium-emphasis">Reçu le {{ dateFr(detail.cree_le) }}</span>
            </div>
            <div class="mb-3">
              <span class="text-caption text-medium-emphasis mr-2">Recours lié à :</span>
              <template v-if="detail.source">
                <v-chip size="small" :color="detail.source.type === 'reclamation' ? '#00838F' : 'primary'" variant="tonal">
                  {{ detail.source.type === 'reclamation' ? 'Réclamation' : 'Dossier' }} #{{ detail.source.id }}
                </v-chip>
                <span class="text-body-2 text-medium-emphasis ml-2">
                  {{ [detail.source.poste, detail.source.appel, detail.source.statut].filter(Boolean).join(' · ') }}
                </span>
              </template>
              <span v-else class="text-medium-emphasis">source supprimée</span>
            </div>
            <v-alert type="info" variant="tonal" density="compact" class="mb-3" icon="mdi-card-account-details-outline">
              Vérifiez la <strong>date de naissance</strong> ci-dessus avec la pièce d'identité du demandeur.
            </v-alert>
            <v-card variant="tonal" color="grey" class="pa-3 mb-4">
              <div class="text-caption font-weight-bold mb-1">Message</div>
              <div style="white-space: pre-wrap">{{ detail.message }}</div>
            </v-card>

            <v-textarea v-model="reponse" label="Réponse / note interne" rows="3" variant="outlined"
                        :readonly="!auth.peutTraiter" hide-details />
            <div v-if="detail.traite_par" class="text-caption text-medium-emphasis mt-2">
              Traité par {{ detail.traite_par }} le {{ dateFr(detail.traite_le) }}
            </div>
          </template>
        </v-card-text>
        <v-divider />
        <v-card-actions class="pa-3">
          <!-- Actions en mode édition -->
          <template v-if="modeEdition">
            <v-spacer />
            <v-btn variant="text" @click="modeEdition = false">Annuler</v-btn>
            <v-btn color="primary" variant="flat" prepend-icon="mdi-content-save" :loading="enAction" @click="enregistrer">
              Enregistrer
            </v-btn>
          </template>
          <!-- Actions en mode lecture -->
          <template v-else>
            <v-btn v-if="auth.peutTraiter" variant="text" prepend-icon="mdi-pencil" @click="ouvrirEdition">
              Modifier
            </v-btn>
            <v-btn v-if="auth.peutTraiter && detail.statut === 'traite'" variant="text"
                   prepend-icon="mdi-lock-open-variant-outline" :loading="enAction" @click="rouvrir">
              Rouvrir
            </v-btn>
            <v-spacer />
            <v-btn variant="text" @click="dialog = false">Fermer</v-btn>
            <v-btn v-if="auth.peutTraiter && detail.statut !== 'traite'" color="primary" variant="flat"
                   prepend-icon="mdi-check" :loading="enAction" @click="traiter">
              Marquer traité
            </v-btn>
          </template>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snack.show" :color="snack.color" timeout="3000">{{ snack.text }}</v-snackbar>
  </div>
</template>

<style scoped>
.message-court { display: inline-block; max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; vertical-align: bottom; color: #525f71; }
.dn { font-weight: 600; color: #1a237e; }
</style>
