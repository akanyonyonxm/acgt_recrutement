<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api'
import StatutBadge from '../../components/StatutBadge.vue'

const router = useRouter()
const dossiers = ref([])
const appels = ref([])
const statut = ref('depose')
const appel = ref(null)
const chargement = ref(false)

const STATUTS = [
  { value: 'depose', title: 'À valider (déposés)' },
  { value: 'en_examen', title: 'En examen' },
  { value: 'retenu', title: 'Retenus' },
  { value: 'non_retenu', title: 'Non retenus' },
  { value: 'rejete', title: 'Rejetés' },
  { value: '', title: 'Tous' },
]

const ENTETES = [
  { title: '#', key: 'id', width: 70 },
  { title: 'Candidat', key: 'candidat' },
  { title: 'Poste', key: 'poste_libelle' },
  { title: 'Appel', key: 'appel_titre' },
  { title: 'Statut', key: 'statut' },
  { title: 'Déposé le', key: 'cree_le' },
  { title: '', key: 'actions', sortable: false, align: 'end' },
]

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

onMounted(async () => {
  const { data } = await api.get('/appels/')
  appels.value = data.results.map((a) => ({ value: a.id, title: a.titre }))
  await charger()
})

function ouvrir(_, { item }) {
  router.push({ name: 'dossier', params: { id: item.id } })
}
const dateFr = (d) => new Date(d).toLocaleDateString('fr-FR')
</script>

<template>
  <div>
    <div class="d-flex align-center mb-6">
      <v-icon color="primary" size="32" class="mr-3">mdi-check-decagram-outline</v-icon>
      <h1 class="text-h5 font-weight-bold text-primary">Validation des dossiers</h1>
      <v-spacer />
      <v-chip color="primary" variant="tonal">{{ dossiers.length }} dossier(s)</v-chip>
    </div>

    <v-card class="mb-4 pa-4">
      <v-row dense>
        <v-col cols="12" sm="6" md="4">
          <v-select v-model="statut" :items="STATUTS" label="Statut" hide-details @update:modelValue="charger" />
        </v-col>
        <v-col cols="12" sm="6" md="4">
          <v-select v-model="appel" :items="appels" label="Appel à candidature" clearable
                    hide-details @update:modelValue="charger" />
        </v-col>
      </v-row>
    </v-card>

    <v-card>
      <v-data-table
        :headers="ENTETES"
        :items="dossiers"
        :loading="chargement"
        hover
        @click:row="ouvrir"
        no-data-text="Aucun dossier dans cette catégorie."
        items-per-page="25"
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
