<script setup>
import { ref, onMounted } from 'vue'
import api from '../../api'
import StatCard from '../../components/StatCard.vue'

// --- Liste courante ---
const items = ref([])
const total = ref(0)
const loading = ref(false)
const q = ref('')
const page = ref(1)

const ENTETES = [
  { title: 'Nom', key: 'nom' },
  { title: 'Postnom', key: 'postnom' },
  { title: 'Prénom', key: 'prenom' },
  { title: 'Type', key: 'type_libelle' },
  { title: 'Année', key: 'annee' },
  { title: 'Référence', key: 'reference' },
  { title: 'Publié', key: 'est_publie', align: 'center' },
]

async function charger({ page: p } = {}) {
  if (p) page.value = p
  loading.value = true
  try {
    const { data } = await api.get('/eligibilite/', { params: { q: q.value, page: page.value } })
    items.value = data.results
    total.value = data.count
  } finally {
    loading.value = false
  }
}

let minuteur
function rechercher() {
  clearTimeout(minuteur)
  minuteur = setTimeout(() => { page.value = 1; charger() }, 350)
}

// --- Import ---
const fichier = ref(null)
const mode = ref('ajouter')        // 'ajouter' | 'remplacer'
const publier = ref(false)
const enImport = ref(false)
const resultat = ref(null)
const erreur = ref('')
const confirmRemplacer = ref(false)

async function lancerImport() {
  erreur.value = ''
  resultat.value = null
  const f = Array.isArray(fichier.value) ? fichier.value[0] : fichier.value
  if (!f) { erreur.value = 'Choisissez un fichier .xlsx.'; return }
  if (mode.value === 'remplacer' && !confirmRemplacer.value) { confirmRemplacer.value = true; return }

  enImport.value = true
  try {
    const fd = new FormData()
    fd.append('fichier', f)
    fd.append('remplacer', mode.value === 'remplacer')
    fd.append('publier', publier.value)
    const { data } = await api.post('/eligibilite/importer/', fd)
    resultat.value = data
    fichier.value = null
    confirmRemplacer.value = false
    await charger({ page: 1 })
  } catch (e) {
    erreur.value = e.response?.data?.detail || e.response?.data?.fichier?.[0] || 'Import impossible.'
  } finally {
    enImport.value = false
  }
}

onMounted(() => charger())
</script>

<template>
  <div>
    <div class="d-flex align-center mb-5">
      <v-icon color="primary" size="30" class="mr-3">mdi-account-multiple-check-outline</v-icon>
      <h1 class="text-h5 font-weight-bold text-primary">Liste d'éligibilité</h1>
    </div>

    <v-row dense class="mb-5">
      <v-col cols="6" md="3">
        <StatCard icon="mdi-account-group" :value="total" label="Éligibles" description="Dans la liste" color="#1a237e" />
      </v-col>
    </v-row>

    <v-row>
      <!-- Import -->
      <v-col cols="12" md="5">
        <v-card flat border>
          <v-card-title class="text-subtitle-1 font-weight-bold d-flex align-center">
            <v-icon color="primary" class="mr-2">mdi-file-upload-outline</v-icon>
            Importer un fichier Excel
          </v-card-title>
          <v-divider />
          <v-card-text>
            <v-file-input
              v-model="fichier"
              label="Fichier .xlsx"
              accept=".xlsx"
              prepend-icon=""
              prepend-inner-icon="mdi-microsoft-excel"
              variant="outlined"
              density="comfortable"
              show-size
              class="mb-2"
            />

            <div class="text-caption text-medium-emphasis mb-1">Mode d'import</div>
            <v-radio-group v-model="mode" hide-details density="compact" class="mb-3"
                           @update:modelValue="confirmRemplacer = false">
              <v-radio value="ajouter" color="primary">
                <template #label>
                  <span><strong>Ajouter</strong> à la liste existante</span>
                </template>
              </v-radio>
              <v-radio value="remplacer" color="error">
                <template #label>
                  <span><strong>Remplacer</strong> toute la liste</span>
                </template>
              </v-radio>
            </v-radio-group>

            <v-checkbox v-model="publier" color="primary" hide-details density="compact"
                        label="Publier (afficher publiquement) les lignes importées" class="mb-2" />

            <v-alert v-if="mode === 'remplacer' && confirmRemplacer" type="warning"
                     variant="tonal" density="compact" class="mb-3">
              ⚠️ Cela supprimera toutes les {{ total }} lignes actuelles. Cliquez à nouveau sur
              « Importer » pour confirmer.
            </v-alert>

            <v-alert v-if="erreur" type="error" variant="tonal" density="compact" class="mb-3">
              {{ erreur }}
            </v-alert>

            <v-alert v-if="resultat" type="success" variant="tonal" density="compact" class="mb-3">
              {{ resultat.importes }} personne(s) importée(s)<template v-if="resultat.supprimes">,
              {{ resultat.supprimes }} ancienne(s) supprimée(s)</template><template v-if="resultat.ignorees">,
              {{ resultat.ignorees }} ligne(s) sans nom ignorée(s)</template><template v-if="resultat.publier"> et publiée(s)</template>.
            </v-alert>

            <v-btn :color="mode === 'remplacer' && confirmRemplacer ? 'error' : 'primary'"
                   variant="flat" block :loading="enImport"
                   :prepend-icon="mode === 'remplacer' && confirmRemplacer ? 'mdi-alert' : 'mdi-upload'"
                   @click="lancerImport">
              {{ mode === 'remplacer' && confirmRemplacer ? 'Confirmer le remplacement' : 'Importer' }}
            </v-btn>
          </v-card-text>
          <v-divider />
          <v-card-text class="text-caption text-medium-emphasis">
            Colonnes attendues (1re ligne = en-têtes) :
            <code>nom · postnom · prenom · type · annee · reference</code>.
            Seul « nom » est obligatoire ; « type » accepte « stage » ou « candidature ».
            <div class="mt-3">
              <v-btn variant="tonal" color="primary" size="small" prepend-icon="mdi-microsoft-excel"
                     href="/api/eligibilite/modele/">
                Télécharger le modèle Excel
              </v-btn>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- Liste courante -->
      <v-col cols="12" md="7">
        <v-card flat border>
          <div class="pa-4 pb-2">
            <v-text-field v-model="q" @update:modelValue="rechercher"
                          label="Rechercher un nom" prepend-inner-icon="mdi-magnify"
                          variant="outlined" density="compact" hide-details clearable
                          @click:clear="rechercher" />
          </div>
          <v-data-table-server
            :headers="ENTETES"
            :items="items"
            :items-length="total"
            :loading="loading"
            :items-per-page="10"
            :items-per-page-options="[{ value: 10, title: '10 par page' }, { value: 25, title: '25 par page' }]"
            @update:options="charger"
            no-data-text="Aucune personne. Importez un fichier pour démarrer."
            class="tableau-admin"
          >
            <template #item.nom="{ item }">
              <span class="font-weight-bold text-primary">{{ item.nom }}</span>
            </template>
            <template #item.annee="{ item }">{{ item.annee || '—' }}</template>
            <template #item.reference="{ item }">{{ item.reference || '—' }}</template>
            <template #item.est_publie="{ item }">
              <v-icon :color="item.est_publie ? 'success' : 'grey-lighten-1'" size="small">
                {{ item.est_publie ? 'mdi-check-circle' : 'mdi-minus-circle-outline' }}
              </v-icon>
            </template>
          </v-data-table-server>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<style scoped>
.tableau-admin :deep(thead th) { background: #f4f5f9; font-weight: 700 !important; color: #1a237e !important; text-transform: uppercase; font-size: 0.72rem; letter-spacing: 0.03em; }
code { background: #eef0f6; padding: 1px 5px; border-radius: 4px; font-size: 0.85em; }
</style>
