<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api'
import StatutBadge from '../../components/StatutBadge.vue'
import StatCard from '../../components/StatCard.vue'

const router = useRouter()
const dossiers = ref([])
const appels = ref([])
const statut = ref('depose')
const appel = ref(null)
const q = ref('')
const chargement = ref(false)
const total = ref(0)
const stats = ref({ total: 0, par_statut: {} })

const KPIS = [
  { key: '', label: 'Total', desc: 'Tous les dossiers', icon: 'mdi-folder-multiple', color: '#1a237e' },
  { key: 'depose', label: 'À valider', desc: 'En attente', icon: 'mdi-inbox-arrow-down', color: '#EF6C00' },
  { key: 'en_examen', label: 'En examen', desc: 'En cours', icon: 'mdi-magnify-scan', color: '#0288D1' },
  { key: 'retenu', label: 'Retenus', desc: 'Candidats retenus', icon: 'mdi-check-circle', color: '#2E7D32' },
  { key: 'non_retenu', label: 'Non retenus', desc: 'Écartés', icon: 'mdi-close-circle', color: '#C62828' },
  { key: 'rejete', label: 'Rejetés', desc: 'Refusés', icon: 'mdi-cancel', color: '#607D8B' },
]
const compte = (key) => (key === '' ? stats.value.total : stats.value.par_statut[key] || 0)

const ENTETES = [
  { title: 'Code', key: 'code', width: 110 },
  { title: 'Candidat', key: 'candidat', sortable: true },
  { title: 'Éligibilité', key: 'correspondance', sortable: false },
  { title: 'Poste', key: 'poste_libelle' },
  { title: 'Appel', key: 'appel_titre' },
  { title: 'Statut', key: 'statut' },
  { title: 'Déposé le', key: 'cree_le' },
  { title: '', key: 'actions', sortable: false, align: 'end' },
]

// Badge de correspondance avec la liste d'éligibilité (indicatif, jamais
// bloquant) : aide l'agent à prioriser sans remplacer son contrôle.
const CORRESPONDANCE = {
  rattache: { libelle: 'Rattaché', color: 'success', icon: 'mdi-link-variant', variant: 'flat' },
  code: { libelle: 'Code reconnu', color: 'success', icon: 'mdi-check', variant: 'tonal' },
  nom: { libelle: 'Nom trouvé', color: 'warning', icon: 'mdi-account-search', variant: 'tonal' },
  aucune: { libelle: 'Aucune', color: 'error', icon: 'mdi-help-circle-outline', variant: 'tonal' },
}

// Mappe la clé de colonne triée -> champ de tri côté API (allowlist backend).
const TRI = {
  code: 'code', candidat: 'nom', poste_libelle: 'poste__libelle',
  appel_titre: 'appel__titre', statut: 'statut', cree_le: 'cree_le',
}

// Clé réactive : tout changement de filtre/recherche recharge le tableau (page 1).
const cle = computed(() => `${statut.value}|${appel.value || ''}|${q.value}`)

async function charger({ page = 1, itemsPerPage = 25, sortBy = [] } = {}) {
  chargement.value = true
  try {
    const params = { page, page_size: itemsPerPage > 0 ? itemsPerPage : 25 }
    if (statut.value) params.statut = statut.value
    if (appel.value) params.appel = appel.value
    if (q.value) params.q = q.value
    if (sortBy.length && TRI[sortBy[0].key]) {
      params.ordering = (sortBy[0].order === 'desc' ? '-' : '') + TRI[sortBy[0].key]
    }
    const { data } = await api.get('/dossiers/', { params })
    dossiers.value = data.results
    total.value = data.count
  } finally {
    chargement.value = false
  }
}

async function chargerStats() {
  const params = {}
  if (appel.value) params.appel = appel.value
  const { data } = await api.get('/dossiers/stats/', { params })
  stats.value = data
}

function filtrer(key) { statut.value = key }     // -> cle change -> tableau rechargé
function changerAppel() { chargerStats() }        // le tableau se recharge via cle

let minuteur
function rechercher() {
  clearTimeout(minuteur)
  minuteur = setTimeout(() => { q.value = q.value.trim() }, 300)
}

function ouvrir(_, { item }) { router.push({ name: 'dossier', params: { id: item.id } }) }
const dateFr = (d) => new Date(d).toLocaleDateString('fr-FR')

onMounted(async () => {
  const { data } = await api.get('/appels/')
  appels.value = data.results.map((a) => ({ value: a.id, title: a.titre }))
  chargerStats()
})
</script>

<template>
  <div>
    <!-- En-tête -->
    <div class="d-flex align-center flex-wrap ga-3 mb-5">
      <v-icon color="primary" size="30" class="mr-1">mdi-check-decagram-outline</v-icon>
      <h1 class="text-h5 font-weight-bold text-primary">Validation des dossiers</h1>
      <v-spacer />
      <v-text-field v-model="q" @update:modelValue="rechercher"
                    placeholder="Rechercher un candidat…" prepend-inner-icon="mdi-magnify"
                    variant="outlined" density="compact" hide-details clearable
                    style="max-width: 280px" @click:clear="q = ''" />
      <v-select v-model="appel" :items="appels" label="Filtrer par appel" clearable hide-details
                density="compact" variant="outlined" style="max-width: 240px"
                @update:modelValue="changerAppel" />
    </div>

    <!-- KPI -->
    <v-row dense class="mb-5">
      <v-col v-for="k in KPIS" :key="k.key" cols="6" sm="4" md="2">
        <StatCard :icon="k.icon" :value="compte(k.key)" :label="k.label" :description="k.desc"
                  :color="k.color" clickable :active="statut === k.key" @click="filtrer(k.key)" />
      </v-col>
    </v-row>

    <!-- Tableau -->
    <v-card flat border>
      <v-data-table-server
        :headers="ENTETES"
        :items="dossiers"
        :items-length="total"
        :loading="chargement"
        :search="cle"
        :items-per-page="25"
        :items-per-page-options="[{ value: 25, title: '25' }, { value: 50, title: '50' }, { value: 100, title: '100' }]"
        @update:options="charger"
        @click:row="ouvrir"
        hover
        no-data-text="Aucun dossier dans cette catégorie."
        loading-text="Chargement…"
        class="tableau-admin"
      >
        <template #item.code="{ item }">
          <span class="font-weight-bold text-primary">{{ item.code || ('#' + item.id) }}</span>
        </template>
        <template #item.candidat="{ item }">
          <span class="font-weight-bold">{{ item.nom }}</span> {{ item.postnom }} {{ item.prenom }}
        </template>
        <template #item.correspondance="{ item }">
          <v-chip :color="CORRESPONDANCE[item.correspondance]?.color || 'grey'"
                  :variant="CORRESPONDANCE[item.correspondance]?.variant || 'tonal'"
                  :prepend-icon="CORRESPONDANCE[item.correspondance]?.icon"
                  size="small" label>
            {{ CORRESPONDANCE[item.correspondance]?.libelle || '—' }}
          </v-chip>
        </template>
        <template #item.poste_libelle="{ item }">{{ item.poste_libelle || '—' }}</template>
        <template #item.statut="{ item }">
          <StatutBadge :statut="item.statut" :libelle="item.statut_libelle" />
        </template>
        <template #item.cree_le="{ item }">
          <span class="text-medium-emphasis">{{ dateFr(item.cree_le) }}</span>
        </template>
        <template #item.actions="{ item }">
          <v-btn color="primary" variant="text" size="small" append-icon="mdi-arrow-right"
                 :to="{ name: 'dossier', params: { id: item.id } }" @click.stop>Ouvrir</v-btn>
        </template>
      </v-data-table-server>
    </v-card>
  </div>
</template>

<style scoped>
.tableau-admin :deep(thead th) { background: #f4f5f9; font-weight: 700 !important; color: #1a237e !important; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.03em; }
.tableau-admin :deep(tbody tr) { cursor: pointer; }
</style>
