<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api'
import StatutBadge from '../../components/StatutBadge.vue'
import StatCard from '../../components/StatCard.vue'

const router = useRouter()
const dossiers = ref([])
const appels = ref([])
const statut = ref('depose')
const appel = ref(null)
const chargement = ref(false)
const stats = ref({ total: 0, par_statut: {} })

const KPIS = [
  { key: '', label: 'Total', icon: 'mdi-folder-multiple', color: '#1a237e' },
  { key: 'depose', label: 'À valider', icon: 'mdi-inbox-arrow-down', color: '#FBC02D' },
  { key: 'en_examen', label: 'En examen', icon: 'mdi-magnify-scan', color: '#0288D1' },
  { key: 'retenu', label: 'Retenus', icon: 'mdi-check-circle', color: '#388E3C' },
  { key: 'non_retenu', label: 'Non retenus', icon: 'mdi-close-circle', color: '#D32F2F' },
  { key: 'rejete', label: 'Rejetés', icon: 'mdi-cancel', color: '#9E9E9E' },
]
const compte = (key) => (key === '' ? stats.value.total : stats.value.par_statut[key] || 0)

const ENTETES = [
  { title: '#', key: 'id', width: 70 },
  { title: 'Candidat', key: 'candidat' },
  { title: 'Poste', key: 'poste_libelle' },
  { title: 'Appel', key: 'appel_titre' },
  { title: 'Statut', key: 'statut' },
  { title: 'Déposé le', key: 'cree_le' },
  { title: '', key: 'actions', sortable: false, align: 'end' },
]

async function chargerStats() {
  const params = {}
  if (appel.value) params.appel = appel.value
  const { data } = await api.get('/dossiers/stats/', { params })
  stats.value = data
}
async function charger() {
  chargement.value = true
  try {
    const params = {}
    if (statut.value) params.statut = statut.value
    if (appel.value) params.appel = appel.value
    const { data } = await api.get('/dossiers/', { params })
    dossiers.value = data.results
  } finally {
    chargement.value = false
  }
}
function filtrer(key) { statut.value = key; charger() }
function changerAppel() { charger(); chargerStats() }

onMounted(async () => {
  const { data } = await api.get('/appels/')
  appels.value = data.results.map((a) => ({ value: a.id, title: a.titre }))
  await Promise.all([charger(), chargerStats()])
})

function ouvrir(_, { item }) { router.push({ name: 'dossier', params: { id: item.id } }) }
const dateFr = (d) => new Date(d).toLocaleDateString('fr-FR')
</script>

<template>
  <div>
    <div class="d-flex align-center mb-5">
      <v-icon color="primary" size="30" class="mr-3">mdi-check-decagram-outline</v-icon>
      <h1 class="text-h5 font-weight-bold text-primary">Validation des dossiers</h1>
      <v-spacer />
      <v-select v-model="appel" :items="appels" label="Filtrer par appel" clearable hide-details
                density="compact" variant="outlined" style="max-width: 280px" @update:modelValue="changerAppel" />
    </div>

    <!-- KPI statistiques -->
    <v-row dense class="mb-5">
      <v-col v-for="k in KPIS" :key="k.key" cols="6" sm="4" md="2">
        <StatCard :icon="k.icon" :value="compte(k.key)" :label="k.label" :color="k.color"
                  clickable :active="statut === k.key" @click="filtrer(k.key)" />
      </v-col>
    </v-row>

    <!-- Tableau -->
    <v-card flat border>
      <v-data-table
        :headers="ENTETES"
        :items="dossiers"
        :loading="chargement"
        hover
        @click:row="ouvrir"
        no-data-text="Aucun dossier dans cette catégorie."
        items-per-page="25"
        class="tableau-admin"
      >
        <template #item.candidat="{ item }">
          <span class="font-weight-bold">{{ item.nom }}</span> {{ item.postnom }} {{ item.prenom }}
        </template>
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
      </v-data-table>
    </v-card>
  </div>
</template>

<style scoped>
.tableau-admin :deep(thead th) { background: #f4f5f9; font-weight: 700 !important; color: #1a237e !important; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.03em; }
.tableau-admin :deep(tbody tr) { cursor: pointer; }
</style>
