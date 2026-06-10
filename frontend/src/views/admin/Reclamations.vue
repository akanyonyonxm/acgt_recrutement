<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../../api'
import StatCard from '../../components/StatCard.vue'

const reclamations = ref([])
const total = ref(0)
const chargement = ref(false)
const statut = ref('en_attente')
const appel = ref(null)
const q = ref('')
const appels = ref([])
const postes = ref([])
const stats = ref({ total: 0, par_statut: {} })
const snack = ref({ show: false, color: 'success', text: '' })

// Détail / décision
const detail = ref(null)
const dialog = ref(false)
const posteChoisi = ref(null)
const motifRejet = ref('')
const action = ref(null)         // 'valider' | 'rejeter'
const enCours = ref(false)

const KPIS = [
  { key: '', label: 'Total', desc: 'Toutes', icon: 'mdi-account-alert-outline', color: '#1a237e' },
  { key: 'en_attente', label: 'En attente', desc: 'À traiter', icon: 'mdi-clock-outline', color: '#EF6C00' },
  { key: 'validee', label: 'Validées', desc: 'Retenues', icon: 'mdi-check-circle', color: '#2E7D32' },
  { key: 'rejetee', label: 'Rejetées', desc: 'Refusées', icon: 'mdi-close-circle', color: '#C62828' },
]
const compte = (k) => (k === '' ? stats.value.total : stats.value.par_statut[k] || 0)
const COULEUR = { en_attente: 'warning', validee: 'success', rejetee: 'error' }

const ENTETES = [
  { title: '#', key: 'id', width: 60 },
  { title: 'Personne', key: 'personne', sortable: false },
  { title: 'Appel', key: 'appel_titre' },
  { title: 'Contact', key: 'email' },
  { title: 'Statut', key: 'statut' },
  { title: 'Reçue le', key: 'cree_le' },
  { title: '', key: 'actions', sortable: false, align: 'end' },
]

const notifier = (text, color = 'success') => (snack.value = { show: true, color, text })
const dateFr = (d) => new Date(d).toLocaleDateString('fr-FR')
const lienDoc = (recId, docId) => `/api/reclamations/${recId}/documents/${docId}/`
const ICONE_DOC = { accuse: 'mdi-file-certificate-outline', cv: 'mdi-file-account-outline', identite: 'mdi-card-account-details-outline', diplome: 'mdi-school-outline' }
const kos = (o) => (o > 1048576 ? (o / 1048576).toFixed(1) + ' Mo' : Math.round(o / 1024) + ' Ko')

async function chargerStats() {
  const { data } = await api.get('/reclamations/stats/')
  stats.value = data
}
async function charger() {
  chargement.value = true
  try {
    const params = {}
    if (statut.value) params.statut = statut.value
    if (appel.value) params.appel = appel.value
    if (q.value) params.q = q.value
    const { data } = await api.get('/reclamations/', { params })
    reclamations.value = data.results
    total.value = data.count
  } finally {
    chargement.value = false
  }
}
function filtrer(k) { statut.value = k; charger() }

let minuteur
function rechercher() { clearTimeout(minuteur); minuteur = setTimeout(() => { q.value = q.value.trim(); charger() }, 300) }

function ouvrir(rec) {
  detail.value = rec
  action.value = null
  posteChoisi.value = null
  motifRejet.value = ''
  dialog.value = true
}

async function confirmer() {
  enCours.value = true
  try {
    if (action.value === 'valider') {
      await api.post(`/reclamations/${detail.value.id}/valider/`,
        posteChoisi.value ? { poste_id: posteChoisi.value } : {})
      notifier('Réclamation validée — la personne est désormais retenue.')
    } else {
      if (!motifRejet.value.trim()) { notifier('Le motif est obligatoire.', 'error'); enCours.value = false; return }
      await api.post(`/reclamations/${detail.value.id}/rejeter/`, { motif: motifRejet.value })
      notifier('Réclamation rejetée.')
    }
    dialog.value = false
    await Promise.all([charger(), chargerStats()])
  } catch (e) {
    notifier(e.response?.data?.detail || e.response?.data?.motif?.[0] || 'Action impossible.', 'error')
  } finally {
    enCours.value = false
  }
}

onMounted(async () => {
  const [a, p] = await Promise.all([api.get('/appels/'), api.get('/postes/')])
  appels.value = a.data.results.map((x) => ({ value: x.id, title: x.titre }))
  postes.value = p.data.results.map((x) => ({ value: x.id, title: x.libelle }))
  await Promise.all([charger(), chargerStats()])
})
</script>

<template>
  <div>
    <div class="d-flex align-center flex-wrap ga-3 mb-5">
      <v-icon color="primary" size="30" class="mr-1">mdi-account-alert-outline</v-icon>
      <h1 class="text-h5 font-weight-bold text-primary">Réclamations d'éligibilité</h1>
      <v-spacer />
      <v-text-field v-model="q" @update:modelValue="rechercher" placeholder="Rechercher un nom…"
                    prepend-inner-icon="mdi-magnify" variant="outlined" density="compact" hide-details clearable
                    style="max-width: 260px" @click:clear="q = ''; charger()" />
      <v-select v-model="appel" :items="appels" label="Appel" clearable hide-details density="compact"
                variant="outlined" style="max-width: 220px" @update:modelValue="charger" />
    </div>

    <!-- KPI -->
    <v-row dense class="mb-5">
      <v-col v-for="k in KPIS" :key="k.key" cols="6" md="3">
        <StatCard :icon="k.icon" :value="compte(k.key)" :label="k.label" :description="k.desc"
                  :color="k.color" clickable :active="statut === k.key" @click="filtrer(k.key)" />
      </v-col>
    </v-row>

    <!-- Tableau -->
    <v-card flat border>
      <v-data-table :headers="ENTETES" :items="reclamations" :loading="chargement"
                    items-per-page="25" hover class="tableau-admin"
                    no-data-text="Aucune réclamation dans cette catégorie.">
        <template #item.personne="{ item }">
          <span class="font-weight-bold">{{ item.nom }}</span> {{ item.postnom }} {{ item.prenom }}
        </template>
        <template #item.statut="{ item }">
          <v-chip :color="COULEUR[item.statut]" size="small" variant="flat" label>{{ item.statut_libelle }}</v-chip>
        </template>
        <template #item.cree_le="{ item }">
          <span class="text-medium-emphasis">{{ dateFr(item.cree_le) }}</span>
        </template>
        <template #item.actions="{ item }">
          <v-btn color="primary" variant="text" size="small" append-icon="mdi-arrow-right" @click="ouvrir(item)">
            Examiner
          </v-btn>
        </template>
      </v-data-table>
    </v-card>

    <!-- Détail / décision -->
    <v-dialog v-model="dialog" max-width="560">
      <v-card v-if="detail" flat border rounded="lg">
        <v-card-title class="d-flex align-center ga-2 py-4">
          <v-icon color="primary">mdi-account-alert-outline</v-icon>
          <span class="font-weight-bold">Réclamation #{{ detail.id }}</span>
          <v-chip :color="COULEUR[detail.statut]" size="small" variant="flat" label class="ml-1">
            {{ detail.statut_libelle }}
          </v-chip>
        </v-card-title>
        <v-divider />
        <v-card-text>
          <div class="info-l"><span>Personne</span><strong>{{ detail.nom }} {{ detail.postnom }} {{ detail.prenom }}</strong></div>
          <div class="info-l"><span>Appel</span><strong>{{ detail.appel_titre }}</strong></div>
          <div class="info-l"><span>Email</span><strong>{{ detail.email }}</strong></div>
          <div class="info-l"><span>Téléphone</span><strong>{{ detail.telephone || '—' }}</strong></div>
          <div v-if="detail.message" class="info-l"><span>Message</span><strong>{{ detail.message }}</strong></div>
          <div class="info-l"><span>Reçue le</span><strong>{{ dateFr(detail.cree_le) }}</strong></div>

          <div class="text-caption text-medium-emphasis mt-3 mb-1">
            Justificatifs ({{ detail.documents?.length || 0 }})
          </div>
          <a v-for="doc in detail.documents" :key="doc.id" class="doc-l"
             :href="lienDoc(detail.id, doc.id)" target="_blank">
            <v-icon size="20" color="primary" class="mr-2">{{ ICONE_DOC[doc.type] || 'mdi-file' }}</v-icon>
            <span class="flex-grow-1">
              <strong>{{ doc.type_libelle }}</strong>
              <span class="text-medium-emphasis"> — {{ doc.nom_original }} · {{ kos(doc.taille) }}</span>
            </span>
            <v-icon size="18" color="primary">mdi-download</v-icon>
          </a>

          <template v-if="detail.statut === 'en_attente'">
            <v-divider class="my-4" />
            <!-- Choix de l'action -->
            <div v-if="!action" class="d-flex ga-3">
              <v-btn color="success" variant="flat" prepend-icon="mdi-check" @click="action = 'valider'">Valider</v-btn>
              <v-btn color="error" variant="outlined" prepend-icon="mdi-close" @click="action = 'rejeter'">Rejeter</v-btn>
            </div>
            <!-- Validation -->
            <div v-else-if="action === 'valider'">
              <v-alert type="info" variant="tonal" density="compact" class="mb-3">
                La personne sera ajoutée aux <strong>retenus</strong> (un dossier est créé et marqué retenu).
              </v-alert>
              <v-select v-model="posteChoisi" :items="postes" label="Poste visé (facultatif)" clearable hide-details />
            </div>
            <!-- Rejet -->
            <div v-else>
              <v-textarea v-model="motifRejet" label="Motif du rejet (obligatoire)" rows="3" autofocus hide-details />
            </div>
          </template>
          <template v-else>
            <v-divider class="my-4" />
            <div v-if="detail.motif" class="info-l"><span>Motif</span><strong>{{ detail.motif }}</strong></div>
            <div class="info-l"><span>Traité par</span><strong>{{ detail.traite_par || '—' }}</strong></div>
          </template>
        </v-card-text>
        <v-card-actions class="px-4 pb-4">
          <v-btn variant="text" @click="dialog = false">Fermer</v-btn>
          <v-spacer />
          <v-btn v-if="action === 'valider'" color="success" variant="flat" :loading="enCours" @click="confirmer">
            Confirmer la validation
          </v-btn>
          <v-btn v-else-if="action === 'rejeter'" color="error" variant="flat" :loading="enCours" @click="confirmer">
            Confirmer le rejet
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snack.show" :color="snack.color" timeout="3500">{{ snack.text }}</v-snackbar>
  </div>
</template>

<style scoped>
.tableau-admin :deep(thead th) { background: #f4f5f9; font-weight: 700 !important; color: #1a237e !important; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.03em; }
.info-l { display: flex; justify-content: space-between; gap: 16px; padding: 7px 0; border-bottom: 1px solid #f0f1f4; font-size: 0.9rem; }
.info-l span { color: #767683; }
.info-l strong { color: #1f2933; text-align: right; }
.doc-l { display: flex; align-items: center; gap: 4px; padding: 9px 12px; margin-bottom: 6px; border: 1px solid #e4e1ea; border-radius: 10px; text-decoration: none; color: inherit; font-size: 0.85rem; transition: background 0.15s, border-color 0.15s; }
.doc-l:hover { background: #f0f3fb; border-color: #c9d4ee; }
</style>
