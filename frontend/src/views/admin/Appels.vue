<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../../api'
import StatCard from '../../components/StatCard.vue'

const appels = ref([])
const chargement = ref(true)

const nbAppels = computed(() => appels.value.length)
const nbPublies = computed(() => appels.value.filter((a) => a.statut === 'publie').length)
const nbListesRetenus = computed(() => appels.value.filter((a) => a.liste_retenus_publiee).length)
const totalDossiers = computed(() => appels.value.reduce((s, a) => s + (a.nb_dossiers || 0), 0))

const ENTETES = [
  { title: 'Titre', key: 'titre' },
  { title: 'Statut', key: 'statut' },
  { title: 'Pièces exigées', key: 'pieces', sortable: false },
  { title: 'Dossiers', key: 'nb_dossiers', align: 'center' },
  { title: 'Retenus publiés', key: 'liste_retenus_publiee', align: 'center' },
]

onMounted(async () => {
  try {
    const { data } = await api.get('/appels/')
    appels.value = data.results
  } finally {
    chargement.value = false
  }
})
</script>

<template>
  <div>
    <div class="d-flex align-center mb-5">
      <v-icon color="primary" size="30" class="mr-3">mdi-bullhorn-outline</v-icon>
      <h1 class="text-h5 font-weight-bold text-primary">Appels à candidature</h1>
      <v-spacer />
      <v-btn color="primary" variant="tonal" prepend-icon="mdi-plus"
             href="/console-3xfk2a/candidatures/appelcandidature/add/" target="_blank">
        Nouvel appel
      </v-btn>
    </div>

    <!-- KPI statistiques -->
    <v-row dense class="mb-5">
      <v-col cols="6" md="3"><StatCard icon="mdi-bullhorn" :value="nbAppels" label="Appels" description="Au total" color="#1a237e" /></v-col>
      <v-col cols="6" md="3"><StatCard icon="mdi-earth" :value="nbPublies" label="Appels publiés" description="Visibles" color="#0288D1" /></v-col>
      <v-col cols="6" md="3"><StatCard icon="mdi-folder-multiple" :value="totalDossiers" label="Dossiers reçus" description="Toutes campagnes" color="#EF6C00" /></v-col>
      <v-col cols="6" md="3"><StatCard icon="mdi-trophy" :value="nbListesRetenus" label="Listes publiées" description="Retenus en ligne" color="#2E7D32" /></v-col>
    </v-row>

    <v-card flat border>
      <v-data-table :headers="ENTETES" :items="appels" :loading="chargement"
                    no-data-text="Aucun appel. Créez-en un dans l'admin Django." items-per-page="25"
                    class="tableau-admin">
        <template #item.titre="{ item }">
          <span class="font-weight-bold">{{ item.titre }}</span>
        </template>
        <template #item.statut="{ item }">
          <v-chip :color="item.statut === 'publie' ? 'success' : 'grey'" size="small" variant="flat" label>
            {{ item.statut_libelle }}
          </v-chip>
        </template>
        <template #item.pieces="{ item }">
          <span class="text-medium-emphasis">
            {{ item.pieces_exigees.map((p) => p.type_piece.libelle).join(', ') || '—' }}
          </span>
        </template>
        <template #item.nb_dossiers="{ item }">
          <v-chip color="primary" size="small" variant="tonal">{{ item.nb_dossiers }}</v-chip>
        </template>
        <template #item.liste_retenus_publiee="{ item }">
          <v-icon :color="item.liste_retenus_publiee ? 'success' : 'grey-lighten-1'">
            {{ item.liste_retenus_publiee ? 'mdi-check-circle' : 'mdi-circle-outline' }}
          </v-icon>
        </template>
      </v-data-table>
    </v-card>

    <p class="text-caption text-medium-emphasis mt-3">
      La création et la configuration fine des appels (dates, pièces exigées) se font dans l'admin technique Django.
    </p>
  </div>
</template>

<style scoped>
.tableau-admin :deep(thead th) { background: #f4f5f9; font-weight: 700 !important; color: #1a237e !important; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.03em; }
</style>
