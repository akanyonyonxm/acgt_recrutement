<script setup>
import { ref, onMounted, computed } from 'vue'
import api from '../../api'
import StatCard from '../../components/StatCard.vue'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()

const appels = ref([])
const appelId = ref(null)
const retenus = ref([])
const total = ref(0)            // vrai nombre de retenus (toutes pages)
const chargement = ref(false)
const q = ref('')
const tri = ref([])
const page = ref(1)
const parPage = ref(25)
const snack = ref({ show: false, color: 'success', text: '' })

const appelCourant = computed(() => appels.value.find((a) => a.id === appelId.value))
const publiee = computed(() => !!appelCourant.value?.liste_retenus_publiee)
const notifier = (text, color = 'success') => (snack.value = { show: true, color, text })

const ENTETES = [
  { title: '#', key: 'rang', sortable: false, width: 64 },
  { title: 'Nom', key: 'nom' },
  { title: 'Postnom', key: 'postnom' },
  { title: 'Prénom', key: 'prenom' },
  { title: 'Poste', key: 'poste_libelle' },
]
// Clé de colonne triée -> champ API (allowlist backend).
const TRI = { nom: 'nom', postnom: 'postnom', prenom: 'prenom', poste_libelle: 'poste__libelle' }

// Clé réactive : recharge la 1ʳᵉ page quand l'appel ou la recherche change.
const cle = computed(() => `${appelId.value || ''}|${q.value}`)

async function rechargerAppels() {
  const { data } = await api.get('/appels/')
  appels.value = data.results
}

async function charger({ page: p = 1, itemsPerPage = 25, sortBy } = {}) {
  if (!appelId.value) { retenus.value = []; total.value = 0; return }
  if (sortBy !== undefined) tri.value = sortBy
  page.value = p
  parPage.value = itemsPerPage > 0 ? itemsPerPage : 25
  chargement.value = true
  try {
    const params = { statut: 'retenu', appel: appelId.value, page: p, page_size: parPage.value }
    if (q.value) params.q = q.value
    const s = tri.value && tri.value[0]
    if (s && TRI[s.key]) params.ordering = (s.order === 'desc' ? '-' : '') + TRI[s.key]
    const { data } = await api.get('/dossiers/', { params })
    retenus.value = data.results
    total.value = data.count
  } finally {
    chargement.value = false
  }
}

let minuteur
function rechercher() { clearTimeout(minuteur); minuteur = setTimeout(() => { q.value = q.value.trim() }, 300) }

async function publier() {
  try {
    const { data } = await api.post(`/appels/${appelId.value}/publier-retenus/`)
    notifier(`Liste publiée — ${data.retenus} retenu(s) désormais visibles publiquement.`)
    await rechargerAppels()
  } catch (e) { notifier(e.response?.data?.detail || 'Publication impossible.', 'error') }
}
async function depublier() {
  try {
    await api.post(`/appels/${appelId.value}/depublier-retenus/`)
    notifier("Liste retirée de l'affichage public.")
    await rechargerAppels()
  } catch (e) { notifier(e.response?.data?.detail || 'Action impossible.', 'error') }
}

onMounted(rechargerAppels)
</script>

<template>
  <div>
    <div class="d-flex align-center mb-5">
      <v-icon color="primary" size="30" class="mr-3">mdi-trophy-outline</v-icon>
      <h1 class="text-h5 font-weight-bold text-primary">Publication des retenus</h1>
    </div>

    <v-card flat border class="pa-4 mb-5">
      <v-select
        v-model="appelId"
        :items="appels.map((a) => ({ value: a.id, title: a.titre + (a.liste_retenus_publiee ? ' — publié' : '') }))"
        label="Appel à candidature" hide-details style="max-width: 460px" />
    </v-card>

    <template v-if="appelId">
      <!-- KPI -->
      <v-row dense class="mb-5">
        <v-col cols="6" md="3">
          <StatCard icon="mdi-account-check" :value="total" label="Personnes retenues"
                    description="Pour cet appel" color="#2E7D32" />
        </v-col>
        <v-col cols="6" md="3">
          <StatCard :icon="publiee ? 'mdi-earth' : 'mdi-earth-off'" :value="publiee ? 'Oui' : 'Non'"
                    label="Liste publiée" :description="publiee ? 'Visible publiquement' : 'Non publiée'"
                    :color="publiee ? '#0288D1' : '#607D8B'" />
        </v-col>
      </v-row>

      <v-card flat border>
        <v-card-title class="d-flex align-center flex-wrap ga-3 py-4">
          <span class="text-subtitle-1 font-weight-bold">Personnes retenues</span>
          <v-chip color="primary" variant="tonal" size="small">{{ total }}</v-chip>
          <v-spacer />
          <v-text-field v-model="q" @update:modelValue="rechercher" placeholder="Rechercher un nom…"
                        prepend-inner-icon="mdi-magnify" variant="outlined" density="compact" hide-details
                        clearable style="max-width: 260px" @click:clear="q = ''" />
          <v-chip v-if="publiee" color="success" variant="flat" prepend-icon="mdi-earth">Liste publiée</v-chip>
          <template v-if="auth.estAdmin">
            <v-btn v-if="!publiee" color="primary" variant="flat"
                   prepend-icon="mdi-publish" :disabled="!total" @click="publier">Publier la liste</v-btn>
            <v-btn v-else color="grey" variant="outlined" prepend-icon="mdi-publish-off" @click="depublier">Dépublier</v-btn>
          </template>
        </v-card-title>
        <v-divider />
        <v-data-table-server
          :headers="ENTETES" :items="retenus" :items-length="total" :loading="chargement"
          :search="cle" :sort-by="tri" :items-per-page="25"
          :items-per-page-options="[{ value: 25, title: '25' }, { value: 50, title: '50' }, { value: 100, title: '100' }]"
          @update:options="charger" class="tableau-admin"
          no-data-text="Aucune personne retenue pour cet appel." loading-text="Chargement…">
          <template #item.rang="{ index }">
            <span class="text-medium-emphasis">{{ (page - 1) * parPage + index + 1 }}</span>
          </template>
          <template #item.nom="{ item }"><span class="font-weight-bold">{{ item.nom }}</span></template>
          <template #item.poste_libelle="{ item }">
            <span class="text-medium-emphasis">{{ item.poste_libelle || '—' }}</span>
          </template>
        </v-data-table-server>
        <v-card-text class="text-caption text-medium-emphasis">
          Publier rend cette liste consultable publiquement (NOM · POSTNOM · PRÉNOM).
          Les candidats retenus ont déjà été notifiés individuellement.
        </v-card-text>
      </v-card>
    </template>

    <v-card v-else flat border class="pa-10 text-center">
      <v-icon size="48" color="grey-lighten-1" class="mb-2">mdi-trophy-outline</v-icon>
      <p class="text-body-2 text-medium-emphasis mb-0">Sélectionnez un appel à candidature pour gérer sa liste de retenus.</p>
    </v-card>

    <v-snackbar v-model="snack.show" :color="snack.color" timeout="3000">{{ snack.text }}</v-snackbar>
  </div>
</template>

<style scoped>
.tableau-admin :deep(thead th) { background: #f4f5f9; font-weight: 700 !important; color: #1a237e !important; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.03em; }
</style>
