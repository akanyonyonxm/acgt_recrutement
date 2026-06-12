<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import api from '../../api'
import StatCard from '../../components/StatCard.vue'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()

const appels = ref([])
const appelId = ref(null)
const retenus = ref([])
const snack = ref({ show: false, color: 'success', text: '' })

const appelCourant = computed(() => appels.value.find((a) => a.id === appelId.value))
const publiee = computed(() => !!appelCourant.value?.liste_retenus_publiee)
const notifier = (text, color = 'success') => (snack.value = { show: true, color, text })

async function rechargerAppels() {
  const { data } = await api.get('/appels/')
  appels.value = data.results
}
async function chargerRetenus() {
  retenus.value = []
  if (!appelId.value) return
  const { data } = await api.get('/dossiers/', { params: { statut: 'retenu', appel: appelId.value } })
  retenus.value = data.results
}

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

watch(appelId, chargerRetenus)
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
          <StatCard icon="mdi-account-check" :value="retenus.length" label="Personnes retenues"
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
          <v-chip color="primary" variant="tonal" size="small">{{ retenus.length }}</v-chip>
          <v-spacer />
          <v-chip v-if="publiee" color="success" variant="flat" prepend-icon="mdi-earth">Liste publiée</v-chip>
          <template v-if="auth.estAdmin">
            <v-btn v-if="!publiee" color="primary" variant="flat"
                   prepend-icon="mdi-publish" :disabled="!retenus.length" @click="publier">Publier la liste</v-btn>
            <v-btn v-else color="grey" variant="outlined" prepend-icon="mdi-publish-off" @click="depublier">Dépublier</v-btn>
          </template>
        </v-card-title>
        <v-divider />
        <v-table class="tableau-admin">
          <thead>
            <tr><th style="width:64px">#</th><th>Nom</th><th>Postnom</th><th>Prénom</th><th>Poste</th></tr>
          </thead>
          <tbody>
            <tr v-for="(d, i) in retenus" :key="d.id">
              <td class="text-medium-emphasis">{{ i + 1 }}</td>
              <td class="font-weight-bold">{{ d.nom }}</td>
              <td>{{ d.postnom }}</td>
              <td>{{ d.prenom }}</td>
              <td class="text-medium-emphasis">{{ d.poste_libelle || '—' }}</td>
            </tr>
            <tr v-if="!retenus.length">
              <td colspan="5" class="text-center text-medium-emphasis py-6">Aucune personne retenue pour cet appel.</td>
            </tr>
          </tbody>
        </v-table>
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
.tableau-admin :deep(thead th), .tableau-admin thead th { background: #f4f5f9; font-weight: 700; color: #1a237e; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.03em; }
</style>
