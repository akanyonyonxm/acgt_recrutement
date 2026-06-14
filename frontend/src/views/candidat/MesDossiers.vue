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
const aBrouillon = computed(() => dossiers.value.some((d) => d.statut === 'brouillon'))

const ACCENT = {
  brouillon: '#90A4AE', depose: '#FBC02D', en_examen: '#0288D1',
  retenu: '#388E3C', non_retenu: '#D32F2F', rejete: '#D32F2F',
}

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
const reference = (d) => `ACGT-${new Date(d.cree_le).getFullYear()}-${String(d.id).padStart(3, '0')}`
// Candidatures clôturées (aucun appel ouvert) vs déjà postulé (appel ouvert mais
// candidature unique déjà utilisée). On distingue pour afficher le bon message.
const cloture = () => cand.charge && !cand.candidaturesOuvertes
const dejaPostule = () => cand.charge && cand.candidaturesOuvertes && !cand.peutPostuler
const bloque = () => cloture() || dejaPostule()
onMounted(charger)
</script>

<template>
  <v-container class="py-8 px-6" style="max-width: 1200px">
    <!-- En-tête -->
    <div class="d-flex align-center flex-wrap ga-4 mb-6">
      <div class="flex-grow-1">
        <h1 class="text-h4 font-weight-bold text-primary">Mes dossiers</h1>
        <p class="text-body-1 text-medium-emphasis mb-0">Gérez vos candidatures et suivez leur évolution.</p>
      </div>
      <v-chip color="primary" variant="tonal" size="large" prepend-icon="mdi-folder-multiple">
        {{ nbActifs }} dossier(s) actif(s)
      </v-chip>
      <v-btn v-if="!bloque()" color="accent" size="large" rounded="lg" class="text-primary font-weight-bold"
             prepend-icon="mdi-plus" :to="{ name: 'postuler' }">
        Déposer un dossier
      </v-btn>
    </div>

    <!-- Bandeau « candidatures clôturées » -->
    <v-alert v-if="cloture()" type="warning" variant="tonal" density="comfortable"
             class="mb-5" icon="mdi-lock-outline">
      Les candidatures sont clôturées. Le dépôt de nouveaux dossiers n'est plus possible.
    </v-alert>

    <!-- Bandeau « déjà postulé » -->
    <v-alert v-else-if="dejaPostule() && dossiers.length" type="info" variant="tonal" density="comfortable"
             class="mb-5" icon="mdi-check-circle-outline">
      Vous avez déjà postulé aux appels à candidature disponibles.
    </v-alert>

    <!-- Aide : suppression des brouillons -->
    <v-alert v-if="!loading && aBrouillon" type="warning" variant="tonal" density="comfortable"
             class="mb-5" icon="mdi-delete-alert-outline">
      Vous pouvez supprimer le dossier <strong>Brouillon</strong> en cliquant sur le petit
      bouton rouge <v-icon size="small" color="error">mdi-delete-outline</v-icon> à droite du dossier.
    </v-alert>

    <div v-if="loading" class="text-center py-10"><v-progress-circular indeterminate color="primary" /></div>

    <!-- Liste des dossiers -->
    <template v-else-if="dossiers.length">
      <v-card v-for="d in dossiers" :key="d.id" class="dossier-carte mb-4"
              :style="{ borderLeftColor: ACCENT[d.statut] }">
        <div class="d-flex align-center flex-wrap ga-4 pa-5">
          <v-avatar :color="ACCENT[d.statut]" variant="tonal" rounded="lg" size="54">
            <v-icon size="28" :color="ACCENT[d.statut]">mdi-account-hard-hat</v-icon>
          </v-avatar>
          <div class="flex-grow-1" style="min-width: 200px">
            <div class="d-flex align-center ga-3 mb-1">
              <span class="ref">DOSSIER {{ d.code || ('#' + reference(d)) }}</span>
              <StatutBadge :statut="d.statut" :libelle="d.statut_libelle" />
            </div>
            <div class="text-h6 font-weight-bold" style="line-height:1.2">
              {{ d.poste_libelle || (d.nom + ' ' + d.prenom) }}
            </div>
            <div class="text-body-2 text-medium-emphasis mt-1 d-flex align-center flex-wrap ga-1">
              <v-icon size="small">mdi-calendar</v-icon>{{ dateFr(d.cree_le) }}
              <v-icon size="small" class="ml-3">mdi-bullhorn-outline</v-icon>{{ d.appel_titre }}
            </div>
          </div>
          <div class="d-flex ga-1">
            <v-btn v-if="d.statut === 'brouillon'" color="primary" variant="outlined" rounded="lg"
                   :to="{ name: 'postuler', query: { dossier: d.id } }" append-icon="mdi-arrow-right">Continuer</v-btn>
            <v-btn v-else color="primary" variant="outlined" rounded="lg"
                   :to="{ name: 'dossier-candidat', params: { id: d.id } }" append-icon="mdi-arrow-right">Voir détails</v-btn>
            <v-btn v-if="d.statut === 'brouillon'" icon="mdi-delete-outline" variant="text" color="error" @click="supprimer(d)" />
          </div>
        </div>
      </v-card>
    </template>

    <!-- État vide -->
    <v-card v-else class="pa-12 text-center" variant="flat" style="border:1px dashed #c6c5d4">
      <v-avatar color="primary" variant="tonal" size="72" class="mb-4"><v-icon size="40">mdi-folder-open-outline</v-icon></v-avatar>
      <h2 class="text-h6 font-weight-bold mb-1">Aucun dossier pour le moment</h2>
      <template v-if="cloture()">
        <p class="text-body-2 text-medium-emphasis mb-0">Les candidatures sont clôturées.</p>
      </template>
      <template v-else>
        <p class="text-body-2 text-medium-emphasis mb-5">Déposez votre première candidature pour démarrer.</p>
        <v-btn color="accent" size="large" rounded="lg" class="text-primary font-weight-bold"
               prepend-icon="mdi-plus" :to="{ name: 'postuler' }">Déposer un dossier</v-btn>
      </template>
    </v-card>
  </v-container>
</template>

<style scoped>
.dossier-carte {
  border: 1px solid #e2e6ea;
  border-left: 4px solid #90A4AE;
  border-radius: 16px;
  transition: box-shadow 0.2s, transform 0.2s;
}
.dossier-carte:hover { box-shadow: 0 10px 28px rgba(26,35,126,0.10); transform: translateY(-2px); }
.ref { font-size: 0.72rem; font-weight: 700; letter-spacing: 0.05em; color: #767683; text-transform: uppercase; }
</style>
