<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api'
import StatutBadge from '../../components/StatutBadge.vue'
import StatCard from '../../components/StatCard.vue'

const router = useRouter()
const dossiers = ref([])
const chargement = ref(false)
const statut = ref('en_examen')
const stats = ref({ total: 0, par_statut: {} })

const KPIS = [
  { key: 'en_examen', label: 'À examiner', icon: 'mdi-magnify-scan', color: '#0288D1' },
  { key: 'retenu', label: 'Retenus', icon: 'mdi-check-circle', color: '#388E3C' },
  { key: 'non_retenu', label: 'Non retenus', icon: 'mdi-close-circle', color: '#D32F2F' },
]
const compte = (key) => stats.value.par_statut[key] || 0

const ENTETES = [
  { title: '#', key: 'id', width: 70 },
  { title: 'Candidat', key: 'candidat' },
  { title: 'Poste', key: 'poste_libelle' },
  { title: 'Appel', key: 'appel_titre' },
  { title: 'Statut', key: 'statut' },
  { title: '', key: 'actions', sortable: false, align: 'end' },
]

async function charger() {
  chargement.value = true
  try {
    const { data } = await api.get('/dossiers/', { params: { statut: statut.value } })
    dossiers.value = data.results
  } finally {
    chargement.value = false
  }
}
async function chargerStats() {
  const { data } = await api.get('/dossiers/stats/')
  stats.value = data
}
function filtrer(key) { statut.value = key; charger() }
function ouvrir(_, { item }) { router.push({ name: 'eval-dossier', params: { id: item.id } }) }

onMounted(async () => { await Promise.all([charger(), chargerStats()]) })
</script>

<template>
  <div>
    <div class="d-flex align-center mb-5">
      <v-icon color="primary" size="30" class="mr-3">mdi-clipboard-text-search-outline</v-icon>
      <h1 class="text-h5 font-weight-bold text-primary">Mes dossiers à examiner</h1>
    </div>

    <v-row dense class="mb-5">
      <v-col v-for="k in KPIS" :key="k.key" cols="6" sm="4" md="3">
        <StatCard :icon="k.icon" :value="compte(k.key)" :label="k.label" :color="k.color"
                  clickable :active="statut === k.key" @click="filtrer(k.key)" />
      </v-col>
    </v-row>

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
        <template #item.actions="{ item }">
          <v-btn color="primary" variant="text" size="small" append-icon="mdi-arrow-right"
                 :to="{ name: 'eval-dossier', params: { id: item.id } }" @click.stop>Examiner</v-btn>
        </template>
      </v-data-table>
    </v-card>
  </div>
</template>

<style scoped>
.tableau-admin :deep(thead th) { background: #f4f5f9; font-weight: 700 !important; color: #1a237e !important; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.03em; }
.tableau-admin :deep(tbody tr) { cursor: pointer; }
</style>
