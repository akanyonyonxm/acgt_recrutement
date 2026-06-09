<script setup>
import { ref, onMounted } from 'vue'
import api from '../../api'

const appels = ref([])
const chargement = ref(true)

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
    <div class="d-flex align-center mb-6">
      <v-icon color="primary" size="32" class="mr-3">mdi-bullhorn-outline</v-icon>
      <h1 class="text-h5 font-weight-bold text-primary">Appels à candidature</h1>
      <v-spacer />
      <v-btn color="primary" variant="tonal" prepend-icon="mdi-plus"
             href="/admin/candidatures/appelcandidature/add/" target="_blank">
        Nouvel appel (admin Django)
      </v-btn>
    </div>

    <v-card>
      <v-data-table :headers="ENTETES" :items="appels" :loading="chargement"
                    no-data-text="Aucun appel. Créez-en un dans l'admin Django." items-per-page="25">
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
