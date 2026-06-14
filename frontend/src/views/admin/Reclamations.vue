<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import api from '../../api'
import StatCard from '../../components/StatCard.vue'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
// Peut traiter (valider/rejeter) une réclamation : admin ou validateur.
const peutTraiter = computed(() => auth.estAdmin || auth.estValidateur)

const reclamations = ref([])
const total = ref(0)
const chargement = ref(false)

// Filtres mémorisés (localStorage) : retrouvés au retour sur la page, pour ne
// pas refiltrer après avoir traité une réclamation. Survit au rechargement.
const STORAGE_FILTRES = 'acgt_filtres_reclamations'
function filtresSauvegardes() {
  try { return JSON.parse(localStorage.getItem(STORAGE_FILTRES)) || {} } catch { return {} }
}
const sauve = filtresSauvegardes()

const statut = ref(sauve.statut ?? 'en_attente')
const appel = ref(sauve.appel ?? null)
const q = ref(sauve.q ?? '')
const dossierDepose = ref(sauve.dossierDepose ?? false)

watch([statut, appel, q, dossierDepose], () => {
  localStorage.setItem(STORAGE_FILTRES, JSON.stringify({
    statut: statut.value, appel: appel.value, q: q.value,
    dossierDepose: dossierDepose.value,
  }))
})
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
  { title: '#', key: 'id', width: 60, sortable: false },
  { title: 'Personne', key: 'personne', sortable: false },
  { title: 'Appel', key: 'appel_titre', sortable: false },
  { title: 'Contact', key: 'email', sortable: false },
  { title: 'Statut', key: 'statut', sortable: false },
  { title: 'Reçue le', key: 'cree_le', sortable: false },
  { title: '', key: 'actions', sortable: false, align: 'end' },
]

const notifier = (text, color = 'success') => (snack.value = { show: true, color, text })
const dateFr = (d) => new Date(d).toLocaleDateString('fr-FR')
const lienDoc = (recId, docId) => `/api/reclamations/${recId}/documents/${docId}/`
const ICONE_DOC = { accuse: 'mdi-file-certificate-outline', cv: 'mdi-file-account-outline', identite: 'mdi-card-account-details-outline', diplome: 'mdi-school-outline' }
const kos = (o) => (o > 1048576 ? (o / 1048576).toFixed(1) + ' Mo' : Math.round(o / 1024) + ' Ko')

// Aperçu des justificatifs (PDF/image) avec navigation.
const apercu = ref({ show: false, index: 0 })
const docCourant = computed(() => detail.value?.documents?.[apercu.value.index] || null)
const estImage = (d) => /\.(png|jpe?g|gif|webp|bmp)$/i.test(d?.nom_original || '')
const urlDocInline = (d) => `${lienDoc(detail.value.id, d.id)}?inline=1`
function ouvrirApercu(i) { apercu.value = { show: true, index: i } }
function naviguerApercu(pas) {
  const n = detail.value.documents.length
  apercu.value.index = (apercu.value.index + pas + n) % n
}

async function chargerStats() {
  const { data } = await api.get('/reclamations/stats/')
  stats.value = data
}

// Clé réactive : tout changement de filtre/recherche recharge le tableau (page 1).
const cle = computed(() => `${statut.value}|${appel.value || ''}|${dossierDepose.value}|${q.value}`)

async function charger({ page = 1, itemsPerPage = 25 } = {}) {
  chargement.value = true
  try {
    const params = { page, page_size: itemsPerPage > 0 ? itemsPerPage : 25 }
    if (statut.value) params.statut = statut.value
    if (appel.value) params.appel = appel.value
    if (dossierDepose.value) params.dossier_depose = 1
    if (q.value) params.q = q.value
    const { data } = await api.get('/reclamations/', { params })
    reclamations.value = data.results
    total.value = data.count
  } finally {
    chargement.value = false
  }
}
function filtrer(k) { statut.value = k }     // -> cle change -> tableau rechargé

let minuteur
function rechercher() { clearTimeout(minuteur); minuteur = setTimeout(() => { q.value = q.value.trim() }, 300) }

const doublonsRec = ref([])
const doublonEnCours = ref(null)
const dossiersDeposes = ref([])
const rejetDossierEnCours = ref(false)
async function ouvrir(rec) {
  detail.value = rec
  action.value = null
  // Pré-sélectionne le poste déclaré par le réclamant (absent sur les
  // anciennes réclamations) ; l'admin peut le changer avant de valider.
  posteChoisi.value = rec.poste || null
  motifRejet.value = ''
  doublonsRec.value = []
  dossiersDeposes.value = []
  dialog.value = true
  if (rec.a_doublon) {
    try { doublonsRec.value = (await api.get(`/reclamations/${rec.id}/doublons/`)).data } catch { /* ignore */ }
  }
  if (rec.a_dossier_depose) {
    try { dossiersDeposes.value = (await api.get(`/reclamations/${rec.id}/dossiers-deposes/`)).data } catch { /* ignore */ }
  }
}

// Rejet en un clic d'une réclamation dont la personne a déjà un dossier déposé.
async function rejeterCarDossier() {
  if (!confirm("Rejeter cette réclamation ? La personne a déjà un dossier déposé "
    + '(elle est déjà candidate). Aucun email ne sera envoyé.')) return
  rejetDossierEnCours.value = true
  try {
    await api.post(`/reclamations/${detail.value.id}/rejeter/`,
      { motif: 'Candidat déjà inscrit (dossier déposé)' })
    notifier('Réclamation rejetée (dossier déjà déposé).')
    dialog.value = false
    await Promise.all([charger(), chargerStats()])
  } catch (e) {
    notifier(e.response?.data?.detail || e.response?.data?.motif || 'Rejet impossible.', 'error')
  } finally {
    rejetDossierEnCours.value = false
  }
}

// Navigation : passer à la prochaine réclamation en attente ayant un doublon.
const enNavRec = ref(false)
async function doublonSuivantRec() {
  enNavRec.value = true
  try {
    const { data } = await api.get('/reclamations/doublon-suivant/', { params: { apres: detail.value.id } })
    if (data.id && data.id !== detail.value.id) {
      const { data: rec } = await api.get(`/reclamations/${data.id}/`)
      await ouvrir(rec)
    } else {
      notifier('Aucune autre réclamation en doublon à traiter.', 'info')
    }
  } finally {
    enNavRec.value = false
  }
}

// Rejet d'un doublon de réclamation en un clic (motif « Réclamation en double »).
async function rejeterDoublonRec(r) {
  if (!confirm(`Rejeter la réclamation de ${r.nom} ${r.prenom} comme doublon ?`)) return
  doublonEnCours.value = r.id
  try {
    await api.post(`/reclamations/${r.id}/rejeter/`, { motif: 'Réclamation en double' })
    notifier('Doublon rejeté.')
    doublonsRec.value = doublonsRec.value.filter((x) => x.id !== r.id)
    await Promise.all([charger(), chargerStats()])
  } catch (e) {
    notifier(e.response?.data?.detail || e.response?.data?.motif?.[0] || 'Rejet impossible.', 'error')
  } finally {
    doublonEnCours.value = null
  }
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
  // Le tableau (v-data-table-server) déclenche le 1er chargement via @update:options.
  chargerStats()
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
                    style="max-width: 260px" @click:clear="q = ''" />
      <v-select v-model="appel" :items="appels" label="Appel" clearable hide-details density="compact"
                variant="outlined" style="max-width: 220px" />
      <v-btn :variant="dossierDepose ? 'flat' : 'outlined'" :color="dossierDepose ? 'deep-orange' : 'grey'"
             prepend-icon="mdi-folder-account-outline" @click="dossierDepose = !dossierDepose">
        A déjà un dossier
      </v-btn>
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
      <v-data-table-server
        :headers="ENTETES" :items="reclamations" :items-length="total" :loading="chargement"
        :search="cle" :items-per-page="25"
        :items-per-page-options="[{ value: 25, title: '25' }, { value: 50, title: '50' }, { value: 100, title: '100' }]"
        @update:options="charger" hover class="tableau-admin"
        no-data-text="Aucune réclamation dans cette catégorie." loading-text="Chargement…">
        <template #item.personne="{ item }">
          <span class="font-weight-bold">{{ item.nom }}</span> {{ item.postnom }} {{ item.prenom }}
          <v-chip v-if="item.a_doublon" color="warning" size="x-small" label variant="tonal"
                  prepend-icon="mdi-content-duplicate" class="ml-1">Doublon</v-chip>
          <v-chip v-if="item.a_dossier_depose" color="deep-orange" size="x-small" label variant="tonal"
                  prepend-icon="mdi-folder-account-outline" class="ml-1">A déjà un dossier</v-chip>
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
      </v-data-table-server>
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
          <div class="info-l"><span>Poste souhaité</span><strong>{{ detail.poste_libelle || '—' }}</strong></div>
          <div class="info-l"><span>Email</span><strong>{{ detail.email }}</strong></div>
          <div class="info-l"><span>Téléphone</span><strong>{{ detail.telephone || '—' }}</strong></div>
          <div v-if="detail.message" class="info-l"><span>Message</span><strong>{{ detail.message }}</strong></div>
          <div class="info-l"><span>Reçue le</span><strong>{{ dateFr(detail.cree_le) }}</strong></div>

          <!-- Doublons : autres réclamations de la même personne -->
          <v-alert v-if="doublonsRec.length" type="warning" variant="tonal" density="compact"
                   class="mt-3" icon="mdi-content-duplicate">
            <div class="font-weight-bold mb-1">
              {{ doublonsRec.length }} autre(s) réclamation(s) de cette personne (même nom).
            </div>
            <div v-for="r in doublonsRec" :key="r.id" class="d-flex align-center ga-2 mt-1">
              <v-chip :color="COULEUR[r.statut]" size="x-small" variant="flat" label>{{ r.statut_libelle }}</v-chip>
              <span class="text-caption flex-grow-1" style="min-width:0">
                <strong>{{ r.nom }} {{ r.postnom }} {{ r.prenom }}</strong>
                <span class="text-medium-emphasis"> · #{{ r.id }} · {{ r.email }}</span>
              </span>
              <v-btn v-if="peutTraiter && r.statut === 'en_attente'" size="x-small" color="error" variant="tonal"
                     :loading="doublonEnCours === r.id" @click="rejeterDoublonRec(r)">
                Rejeter le doublon
              </v-btn>
            </div>
          </v-alert>

          <!-- Croisement : la personne a déjà un dossier déposé -->
          <v-alert v-if="dossiersDeposes.length" type="error" variant="tonal" density="compact"
                   class="mt-3" icon="mdi-folder-account-outline">
            <div class="font-weight-bold mb-1">
              Cette personne a déjà {{ dossiersDeposes.length }} dossier(s) déposé(s) — elle est
              déjà candidate. Cette réclamation est probablement redondante.
            </div>
            <div v-for="d in dossiersDeposes" :key="d.id" class="d-flex align-center ga-2 mt-1">
              <RouterLink :to="{ name: 'dossier', params: { id: d.id } }" class="font-weight-bold lien-dossier">
                {{ d.code || ('#' + d.id) }}
              </RouterLink>
              <span class="text-caption flex-grow-1" style="min-width:0">
                <strong>{{ d.nom }} {{ d.postnom }} {{ d.prenom }}</strong>
                <span class="text-medium-emphasis"> · {{ d.poste_libelle || d.appel_titre }}</span>
              </span>
            </div>
            <v-btn v-if="peutTraiter && detail.statut === 'en_attente'" size="small" color="error" variant="flat"
                   class="mt-3" prepend-icon="mdi-close-circle-outline"
                   :loading="rejetDossierEnCours" @click="rejeterCarDossier">
              Rejeter (déjà un dossier déposé)
            </v-btn>
          </v-alert>

          <div class="text-caption text-medium-emphasis mt-3 mb-1">
            Justificatifs ({{ detail.documents?.length || 0 }})
          </div>
          <div v-for="(doc, i) in detail.documents" :key="doc.id" class="doc-l"
               @click="ouvrirApercu(i)" style="cursor:pointer">
            <v-icon size="20" color="primary" class="mr-2">{{ ICONE_DOC[doc.type] || 'mdi-file' }}</v-icon>
            <span class="flex-grow-1">
              <strong>{{ doc.type_libelle }}</strong>
              <span class="text-medium-emphasis"> — {{ doc.nom_original }} · {{ kos(doc.taille) }}</span>
            </span>
            <v-btn icon="mdi-eye-outline" variant="text" size="x-small" color="primary" @click.stop="ouvrirApercu(i)" />
            <a :href="lienDoc(detail.id, doc.id)" target="_blank" @click.stop>
              <v-btn icon="mdi-download" variant="text" size="x-small" color="primary" />
            </a>
          </div>

          <template v-if="detail.statut === 'en_attente' && peutTraiter">
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
              <v-select v-model="posteChoisi" :items="postes" label="Poste visé" clearable
                        :hint="detail.poste ? 'Pré-rempli avec le poste déclaré par le réclamant.' : 'Non déclaré par le réclamant : choisissez-le si possible.'"
                        persistent-hint />
            </div>
            <!-- Rejet -->
            <div v-else>
              <v-textarea v-model="motifRejet" label="Motif du rejet (obligatoire)" rows="3" autofocus hide-details />
            </div>
          </template>
          <template v-else-if="detail.statut !== 'en_attente'">
            <v-divider class="my-4" />
            <div v-if="detail.motif" class="info-l"><span>Motif</span><strong>{{ detail.motif }}</strong></div>
            <div class="info-l"><span>Traité par</span><strong>{{ detail.traite_par || '—' }}</strong></div>
          </template>
        </v-card-text>
        <v-card-actions class="px-4 pb-4">
          <v-btn variant="text" @click="dialog = false">Fermer</v-btn>
          <v-btn v-if="detail.a_doublon" variant="tonal" color="warning" size="small"
                 prepend-icon="mdi-content-duplicate" append-icon="mdi-arrow-right"
                 :loading="enNavRec" @click="doublonSuivantRec">Doublon suivant</v-btn>
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

    <!-- Aperçu des justificatifs (PDF / image) avec navigation -->
    <v-dialog v-model="apercu.show" max-width="980" scrollable>
      <v-card v-if="docCourant" flat>
        <v-card-title class="d-flex align-center ga-2 py-3">
          <v-icon color="primary">{{ ICONE_DOC[docCourant.type] || 'mdi-file' }}</v-icon>
          <div class="flex-grow-1" style="min-width:0">
            <div class="font-weight-bold">{{ docCourant.type_libelle }}</div>
            <div class="text-caption text-medium-emphasis text-truncate">{{ docCourant.nom_original }}</div>
          </div>
          <v-chip size="small" variant="tonal">{{ apercu.index + 1 }} / {{ detail.documents.length }}</v-chip>
          <a :href="lienDoc(detail.id, docCourant.id)" target="_blank">
            <v-btn icon="mdi-download" variant="text" size="small" />
          </a>
          <v-btn icon="mdi-close" variant="text" size="small" @click="apercu.show = false" />
        </v-card-title>
        <v-divider />
        <div class="apercu-zone">
          <v-btn icon="mdi-chevron-left" variant="elevated" class="nav-btn nav-gauche"
                 :disabled="detail.documents.length < 2" @click="naviguerApercu(-1)" />
          <img v-if="estImage(docCourant)" :src="urlDocInline(docCourant)" class="apercu-img" alt="" />
          <iframe v-else :src="urlDocInline(docCourant)" class="apercu-iframe" title="aperçu" />
          <v-btn icon="mdi-chevron-right" variant="elevated" class="nav-btn nav-droite"
                 :disabled="detail.documents.length < 2" @click="naviguerApercu(1)" />
        </div>
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
.apercu-zone { position: relative; background: #2b2b2b; display: flex; align-items: center; justify-content: center; height: 72vh; overflow: auto; }
.apercu-iframe { width: 100%; height: 100%; border: none; background: #fff; }
.apercu-img { max-width: 100%; max-height: 100%; object-fit: contain; }
.nav-btn { position: absolute; top: 50%; transform: translateY(-50%); z-index: 2; opacity: 0.92; }
.nav-gauche { left: 12px; }
.nav-droite { right: 12px; }
</style>
