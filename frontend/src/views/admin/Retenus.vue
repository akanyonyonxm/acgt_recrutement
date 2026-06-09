<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import api from '../../api'

const appels = ref([])
const appelId = ref(null)
const retenus = ref([])
const snack = ref({ show: false, color: 'success', text: '' })

const appelCourant = computed(() => appels.value.find((a) => a.id === appelId.value))
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
    notifier('Liste retirée de l\'affichage public.')
    await rechargerAppels()
  } catch (e) { notifier(e.response?.data?.detail || 'Action impossible.', 'error') }
}

watch(appelId, chargerRetenus)
onMounted(rechargerAppels)
</script>

<template>
  <div>
    <div class="d-flex align-center mb-6">
      <v-icon color="primary" size="32" class="mr-3">mdi-trophy-outline</v-icon>
      <h1 class="text-h5 font-weight-bold text-primary">Publication des retenus</h1>
    </div>

    <v-card class="pa-4 mb-4">
      <v-select
        v-model="appelId"
        :items="appels.map((a) => ({ value: a.id, title: a.titre + (a.liste_retenus_publiee ? ' — publié' : '') }))"
        label="Appel à candidature" hide-details style="max-width: 460px" />
    </v-card>

    <v-card v-if="appelId">
      <v-card-title class="d-flex align-center flex-wrap ga-3">
        <span class="text-subtitle-1 font-weight-bold">Personnes retenues</span>
        <v-chip color="primary" variant="tonal" size="small">{{ retenus.length }}</v-chip>
        <v-spacer />
        <v-chip v-if="appelCourant?.liste_retenus_publiee" color="success" variant="flat" prepend-icon="mdi-earth">
          Liste publiée
        </v-chip>
        <v-btn v-if="!appelCourant?.liste_retenus_publiee" color="primary" variant="flat"
               prepend-icon="mdi-publish" :disabled="!retenus.length" @click="publier">
          Publier la liste
        </v-btn>
        <v-btn v-else color="grey" variant="outlined" prepend-icon="mdi-publish-off" @click="depublier">
          Dépublier
        </v-btn>
      </v-card-title>
      <v-divider />
      <v-list>
        <v-list-item v-for="d in retenus" :key="d.id">
          <template #prepend><v-icon color="success">mdi-account-check</v-icon></template>
          <v-list-item-title>
            <strong>{{ d.nom }}</strong> {{ d.postnom }} {{ d.prenom }}
          </v-list-item-title>
        </v-list-item>
        <v-list-item v-if="!retenus.length" class="text-medium-emphasis">
          Aucune personne retenue pour cet appel.
        </v-list-item>
      </v-list>
      <v-card-text class="text-caption text-medium-emphasis">
        Publier rend cette liste consultable publiquement (NOM · POSTNOM · PRÉNOM).
        Les candidats retenus ont déjà été notifiés individuellement.
      </v-card-text>
    </v-card>

    <v-snackbar v-model="snack.show" :color="snack.color" timeout="3000">{{ snack.text }}</v-snackbar>
  </div>
</template>
