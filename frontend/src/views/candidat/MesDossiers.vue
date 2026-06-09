<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../../api'
import StatutBadge from '../../components/StatutBadge.vue'
import { useCandidatureStore } from '../../stores/candidature'

const cand = useCandidatureStore()
const dossiers = ref([])
const loading = ref(true)

const ACTIFS = ['brouillon', 'depose', 'en_examen']
const nbActifs = computed(() => dossiers.value.filter((d) => ACTIFS.includes(d.statut)).length)

async function charger() {
  loading.value = true
  try {
    const { data } = await api.get('/dossiers/')
    dossiers.value = data.results
    cand.rafraichir()
  } finally {
    loading.value = false
  }
}
async function supprimer(d) {
  if (!confirm('Supprimer ce brouillon ?')) return
  await api.delete(`/dossiers/${d.id}/`)
  charger()
}
const dateFr = (d) => new Date(d).toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' })
const bloque = () => cand.charge && !cand.peutPostuler
onMounted(charger)
</script>

<template>
  <v-container class="py-8" style="max-width: 1140px">
    <!-- En-tête -->
    <div class="d-flex align-center flex-wrap ga-3 mb-1">
      <div>
        <h1 class="text-h4 font-weight-bold text-primary">Tableau de bord</h1>
        <p class="text-body-1 text-medium-emphasis">Gérez vos candidatures et suivez l'évolution de vos dossiers.</p>
      </div>
      <v-spacer />
      <v-chip color="primary" variant="tonal" size="large" prepend-icon="mdi-folder-multiple">
        {{ nbActifs }} dossier(s) actif(s)
      </v-chip>
    </div>

    <v-row class="mt-2">
      <v-col cols="12">
        <div v-if="loading" class="text-center py-10"><v-progress-circular indeterminate color="primary" /></div>

        <template v-else-if="dossiers.length">
          <v-card v-for="d in dossiers" :key="d.id" class="dossier-carte pa-5 mb-4">
            <div class="d-flex align-center flex-wrap ga-4">
              <v-avatar color="primary" variant="tonal" rounded="lg" size="52">
                <v-icon size="28">mdi-briefcase-outline</v-icon>
              </v-avatar>
              <div class="flex-grow-1" style="min-width: 180px">
                <div class="d-flex align-center ga-2 mb-1">
                  <span class="text-caption font-weight-bold text-medium-emphasis">DOSSIER #{{ d.id }}</span>
                  <StatutBadge :statut="d.statut" :libelle="d.statut_libelle" />
                </div>
                <div class="text-h6 font-weight-bold">{{ d.poste_libelle || (d.nom + ' ' + d.prenom) }}</div>
                <div class="text-caption text-medium-emphasis mt-1">
                  <v-icon size="x-small">mdi-calendar</v-icon> {{ dateFr(d.cree_le) }}
                  · {{ d.appel_titre }}
                </div>
              </div>
              <div class="d-flex ga-2">
                <v-btn v-if="d.statut === 'brouillon'" color="primary" variant="outlined"
                       :to="{ name: 'postuler', query: { dossier: d.id } }" append-icon="mdi-arrow-right">Continuer</v-btn>
                <v-btn v-else color="primary" variant="outlined"
                       :to="{ name: 'dossier-candidat', params: { id: d.id } }" append-icon="mdi-arrow-right">Voir détails</v-btn>
                <v-btn v-if="d.statut === 'brouillon'" icon="mdi-delete" variant="text" color="error" @click="supprimer(d)" />
              </div>
            </div>
          </v-card>
        </template>

        <v-card v-else class="pa-10 text-center">
          <v-icon size="56" color="grey-lighten-1" class="mb-3">mdi-folder-open-outline</v-icon>
          <p class="text-body-1 mb-4">Vous n'avez encore déposé aucun dossier.</p>
        </v-card>

        <div class="d-flex justify-end mt-2">
          <v-btn color="accent" size="large" rounded="lg" class="text-primary font-weight-bold" prepend-icon="mdi-plus"
                 :to="bloque() ? undefined : { name: 'postuler' }" :disabled="bloque()">
            Déposer un nouveau dossier
            <v-tooltip v-if="bloque()" activator="parent" location="bottom">Vous avez déjà postulé aux appels disponibles</v-tooltip>
          </v-btn>
        </div>
      </v-col>
    </v-row>
  </v-container>
</template>

<style scoped>
.dossier-carte { border: 1px solid #e2e6ea; transition: box-shadow 0.2s, transform 0.2s; }
.dossier-carte:hover { box-shadow: 0 8px 24px rgba(26,35,126,0.10); transform: translateY(-2px); }
</style>
