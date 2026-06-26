<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import api from '../../api'
import { useAuthStore } from '../../stores/auth'
import StatCard from '../../components/StatCard.vue'

const auth = useAuthStore()
const monId = computed(() => auth.utilisateur?.id)
// Décision sur un recours précis : admin/superviseur toujours ; un validateur
// seulement si le recours LUI est affecté (cohérent avec le contrôle serveur).
function peutDecider(item) {
  if (auth.peutSuperviser) return true
  return auth.estValidateur && item?.affecte_a === monId.value
}

const STORAGE_FILTRES = `acgt_filtres_recours_${auth.utilisateur?.id ?? 'anon'}`
const sauve = JSON.parse(localStorage.getItem(STORAGE_FILTRES) || '{}')

const recours = ref([])
const total = ref(0)
const chargement = ref(false)
const stats = ref({ total: 0, en_attente: 0, valide: 0, rejete: 0 })

const statut = ref(sauve.statut ?? '')
const q = ref(sauve.q ?? '')
const tri = ref(Array.isArray(sauve.tri) ? sauve.tri : [])
// Filtre d'affectation. Un validateur (non admin/superviseur) voit son lot par
// défaut. '' = tous, 'moi' = mon lot, 'aucune' = non affectés, '<id>' = lot d'un agent.
const affecteParDefaut = (auth.estValidateur && !auth.peutSuperviser) ? 'moi' : ''
const affecte = ref(sauve.affecte ?? affecteParDefaut)
const agents = ref([])   // agents pouvant traiter (admin/superviseur/validateur)

// Répartition de la charge (supervision)
const dialogRepartir = ref(false)
const agentsChoisis = ref([])
const enRepartition = ref(false)
const resultatRepartition = ref(null)
const reequilibrer = ref(false)
// Catégorie déjà décidée (validés / rejetés) : révision réservée aux superviseurs.
const categorieDecidee = computed(() => !['', 'en_attente'].includes(statut.value))
const agentsEligibles = computed(() => agents.value.filter((a) =>
  categorieDecidee.value
    ? (a.roles.includes('admin') || a.roles.includes('superviseur'))
    : true))
const optionsAffecte = computed(() => {
  if (!auth.peutSuperviser) {
    return [{ value: 'moi', title: 'Les miens' }, { value: '', title: 'Tous' }]
  }
  return [
    { value: '', title: 'Tous les agents' },
    { value: 'moi', title: 'Les miens' },
    { value: 'aucune', title: 'Non affectés' },
    ...agents.value.map((a) => ({ value: String(a.id), title: a.nom })),
  ]
})

const detail = ref(null)
const dialog = ref(false)
const reponse = ref('')
const enAction = ref(false)
const snack = ref({ show: false, color: 'success', text: '' })

const notifier = (text, color = 'success') => (snack.value = { show: true, color, text })
const dateFr = (d) => (d ? new Date(d).toLocaleDateString('fr-FR') : '—')
const COULEUR_STATUT = { en_attente: 'warning', valide: 'success', rejete: 'error', traite: 'success' }
// Couleur de chip pour le statut d'un dossier lié (convention métier).
const COULEUR_DOSSIER = {
  brouillon: 'grey', depose: 'info', en_examen: 'warning',
  retenu: 'success', non_retenu: 'orange', rejete: 'error',
}
const COULEUR_STATUT_DOSSIER = (s) => COULEUR_DOSSIER[s] || 'grey'

const headers = [
  { title: 'Personne', key: 'nom' },
  { title: 'Né(e) le', key: 'date_naissance', sortable: false },
  { title: 'Email', key: 'email', sortable: false },
  { title: 'Lié à', key: 'source', sortable: false },
  { title: 'Affecté à', key: 'affecte_a_nom', sortable: false },
  { title: 'Statut', key: 'statut' },
  { title: 'Reçu le', key: 'cree_le' },
  { title: '', key: 'actions', sortable: false, align: 'end' },
]
const TRI = { nom: 'nom', statut: 'statut', cree_le: 'cree_le' }

const cle = computed(() => `${statut.value}|${affecte.value}|${q.value}`)

function memoriser() {
  localStorage.setItem(STORAGE_FILTRES, JSON.stringify({
    statut: statut.value, q: q.value, affecte: affecte.value, tri: tri.value,
  }))
}

async function chargerStats() {
  const { data } = await api.get('/recours/stats/')
  stats.value = data
}

async function charger({ page = 1, itemsPerPage = 25, sortBy } = {}) {
  chargement.value = true
  try {
    if (sortBy !== undefined) tri.value = sortBy
    const params = { page, page_size: itemsPerPage > 0 ? itemsPerPage : 25 }
    if (statut.value) params.statut = statut.value
    if (affecte.value) params.affecte = affecte.value
    if (q.value) params.q = q.value
    const s = tri.value && tri.value[0]
    if (s && TRI[s.key]) params.ordering = (s.order === 'desc' ? '-' : '') + TRI[s.key]
    const { data } = await api.get('/recours/', { params })
    recours.value = data.results
    total.value = data.count
    memoriser()
    chargerStats()
  } finally {
    chargement.value = false
  }
}

function filtrerStatut(s) { statut.value = statut.value === s ? '' : s }

// --- Détail / examen ---
const personne = ref(null)            // { dossiers: [], reclamations: [] }
const chargementPersonne = ref(false)

function ouvrir(r) {
  detail.value = r
  reponse.value = r.reponse || ''
  modeEdition.value = false
  personne.value = null
  dialog.value = true
  chargerPersonne(r.id)
}

async function chargerPersonne(id) {
  chargementPersonne.value = true
  try {
    const { data } = await api.get(`/recours/${id}/personne/`)
    personne.value = data
  } catch {
    personne.value = { dossiers: [], reclamations: [] }
  } finally {
    chargementPersonne.value = false
  }
}

const nbEnregistrements = computed(() =>
  personne.value ? personne.value.dossiers.length + personne.value.reclamations.length : 0)

// --- Aperçu de document (in-app) avec rotation / zoom / téléchargement ---
const EXT_IMAGE = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']
const apercu = ref({ show: false, url: '', urlDl: '', titre: '', estImage: false })
const rotation = ref(0)   // degrés : 0 / 90 / 180 / 270
const zoom = ref(1)       // facteur d'échelle
function voirDocument(doc) {
  const nom = (doc.nom_original || doc.url || '').toLowerCase()
  const ext = nom.split('.').pop().split('?')[0]
  rotation.value = 0
  zoom.value = 1
  apercu.value = {
    show: true,
    url: doc.url + '?inline=1',     // aperçu en ligne
    urlDl: doc.url,                 // sans inline = téléchargement (pièce jointe)
    titre: doc.libelle || doc.nom_original,
    estImage: EXT_IMAGE.includes(ext),
  }
}
const pivoter = (sens) => { rotation.value = (rotation.value + sens * 90 + 360) % 360 }
const zoomer = (pas) => { zoom.value = Math.min(4, Math.max(0.25, +(zoom.value + pas).toFixed(2))) }
const reinitVue = () => { rotation.value = 0; zoom.value = 1 }
const styleImage = computed(() => ({
  transform: `rotate(${rotation.value}deg) scale(${zoom.value})`,
}))

// --- Décision (valider / rejeter) avec confirmation ---
const confirme = ref({ show: false, type: '' })   // type: 'valider' | 'rejeter'
const erreurNote = ref('')
function demanderDecision(type) {
  reponse.value = detail.value.reponse || ''
  erreurNote.value = ''
  confirme.value = { show: true, type }
}

async function confirmerDecision() {
  const type = confirme.value.type
  // Le rejet exige un motif ; la validation accepte une note facultative.
  if (type === 'rejeter' && !reponse.value.trim()) {
    erreurNote.value = 'Le motif du rejet est obligatoire.'
    return
  }
  enAction.value = true
  try {
    const { data } = await api.post(`/recours/${detail.value.id}/${type}/`, { reponse: reponse.value })
    Object.assign(detail.value, data)
    notifier(type === 'valider' ? 'Recours validé (validés après recours).' : 'Recours rejeté.')
    confirme.value.show = false
    dialog.value = false
    charger()
  } catch (e) {
    notifier(e.response?.data?.detail || 'Action impossible.', 'error')
  } finally {
    enAction.value = false
  }
}

async function rouvrir() {
  enAction.value = true
  try {
    const { data } = await api.post(`/recours/${detail.value.id}/rouvrir/`)
    Object.assign(detail.value, data)
    notifier('Recours rouvert (en attente).')
    dialog.value = false
    charger()
  } catch (e) {
    notifier(e.response?.data?.detail || 'Action impossible.', 'error')
  } finally {
    enAction.value = false
  }
}

const nomComplet = (r) => [r.nom, r.postnom, r.prenom].filter(Boolean).join(' ')

// --- Édition d'un recours (identité, contact, message, date de réception) ---
const modeEdition = ref(false)
const edit = ref({})

function ouvrirEdition() {
  edit.value = {
    nom: detail.value.nom, postnom: detail.value.postnom, prenom: detail.value.prenom,
    date_naissance: detail.value.date_naissance,
    email: detail.value.email, message: detail.value.message,
    cree_le: (detail.value.cree_le || '').slice(0, 10),   // YYYY-MM-DD
  }
  modeEdition.value = true
}

async function enregistrer() {
  enAction.value = true
  try {
    const { data } = await api.patch(`/recours/${detail.value.id}/`, edit.value)
    Object.assign(detail.value, data)
    notifier('Recours modifié.')
    modeEdition.value = false
    charger()
  } catch (e) {
    const d = e.response?.data
    notifier(d?.detail || d?.nom?.[0] || d?.prenom?.[0] || d?.message?.[0]
      || d?.cree_le?.[0] || 'Modification impossible.', 'error')
  } finally {
    enAction.value = false
  }
}

// --- Mise à jour du domaine (poste) — admin uniquement ---
const postes = ref([])
const dialogDomaine = ref(false)
const domaineChoisi = ref(null)

function ouvrirDomaine() {
  domaineChoisi.value = detail.value.poste || null   // override existant, sinon vide
  dialogDomaine.value = true
}

async function majDomaine() {
  enAction.value = true
  try {
    const { data } = await api.post(`/recours/${detail.value.id}/domaine/`,
      { poste_id: domaineChoisi.value || null })
    Object.assign(detail.value, data)
    notifier('Domaine mis à jour.')
    dialogDomaine.value = false
    charger()
  } catch (e) {
    notifier(e.response?.data?.detail || 'Mise à jour du domaine impossible.', 'error')
  } finally {
    enAction.value = false
  }
}

// --- Répartition de la charge entre agents (supervision) ---
async function repartir() {
  if (!agentsChoisis.value.length) {
    notifier('Sélectionnez au moins un agent.', 'error'); return
  }
  enRepartition.value = true
  resultatRepartition.value = null
  try {
    const corps = {
      agents: agentsChoisis.value,
      seulement_non_affectes: !reequilibrer.value,
    }
    if (statut.value) corps.statut = statut.value
    if (q.value) corps.q = q.value
    const { data } = await api.post('/recours/repartir/', corps)
    resultatRepartition.value = data
    notifier(`${data.total_reparti} recours réparti(s).`)
    charger()
  } catch (e) {
    notifier(e.response?.data?.agents || e.response?.data?.detail || 'Répartition impossible.', 'error')
  } finally {
    enRepartition.value = false
  }
}

// Recharger quand le filtre d'affectation change (le tableau écoute `cle`).
watch(affecte, () => memoriser())

onMounted(async () => {
  // Référentiel des domaines (postes) — pour la correction du domaine (admin).
  if (auth.estAdmin) {
    try {
      const { data } = await api.get('/postes/', { params: { page_size: 200 } })
      postes.value = data.results || data
    } catch { /* non bloquant */ }
  }
  // Liste des agents pouvant traiter (pour répartir / filtrer) — supervision.
  if (auth.peutSuperviser) {
    try {
      const { data } = await api.get('/auth/utilisateurs/')
      agents.value = data
        .filter((u) => u.roles.includes('admin') || u.roles.includes('superviseur')
          || u.roles.includes('validateur'))
        .map((u) => ({ id: u.id, nom: `${u.prenom} ${u.nom}`.trim() || u.email, roles: u.roles }))
    } catch { /* non bloquant */ }
  }
})
</script>

<template>
  <div>
    <div class="d-flex align-center flex-wrap ga-3 mb-5">
      <v-icon color="primary" size="32">mdi-gavel</v-icon>
      <h1 class="text-h5 font-weight-bold text-primary mb-0">Recours</h1>
      <v-spacer />
      <v-select v-model="affecte" :items="optionsAffecte" label="Affecté à" hide-details density="compact"
                variant="outlined" style="max-width: 220px" />
      <v-btn v-if="auth.peutSuperviser" color="primary" variant="tonal"
             prepend-icon="mdi-account-multiple-check-outline" @click="dialogRepartir = true">
        Répartir
      </v-btn>
      <v-text-field v-model="q" placeholder="Rechercher (nom, email)…"
                    density="compact" variant="outlined" hide-details prepend-inner-icon="mdi-magnify"
                    style="max-width: 280px" clearable />
    </div>

    <!-- KPI -->
    <v-row dense class="mb-4">
      <v-col cols="6" sm="3">
        <StatCard icon="mdi-gavel" :value="stats.total" label="Total recours"
                  description="Tous statuts" color="#5E35B1"
                  clickable :active="statut === ''" @click="filtrerStatut('')" />
      </v-col>
      <v-col cols="6" sm="3">
        <StatCard icon="mdi-clock-outline" :value="stats.en_attente" label="En attente"
                  description="À examiner" color="#EF6C00"
                  clickable :active="statut === 'en_attente'" @click="filtrerStatut('en_attente')" />
      </v-col>
      <v-col cols="6" sm="3">
        <StatCard icon="mdi-check-decagram-outline" :value="stats.valide" label="Validés"
                  description="Validés après recours" color="#2E7D32"
                  clickable :active="statut === 'valide'" @click="filtrerStatut('valide')" />
      </v-col>
      <v-col cols="6" sm="3">
        <StatCard icon="mdi-close-circle-outline" :value="stats.rejete" label="Rejetés"
                  description="Décision défavorable" color="#C62828"
                  clickable :active="statut === 'rejete'" @click="filtrerStatut('rejete')" />
      </v-col>
    </v-row>

    <v-card flat border rounded="lg">
      <v-data-table-server
        :headers="headers" :items="recours" :items-length="total" :loading="chargement"
        :items-per-page="25" :items-per-page-options="[25, 50, 100]"
        :sort-by="tri" :search="cle" @update:options="charger">
        <template #[`item.nom`]="{ item }">
          <span class="font-weight-medium">{{ item.nom }}</span>
          <span class="text-medium-emphasis"> {{ item.postnom }} {{ item.prenom }}</span>
        </template>
        <template #[`item.date_naissance`]="{ item }">{{ dateFr(item.date_naissance) }}</template>
        <template #[`item.email`]="{ item }">{{ item.email || '—' }}</template>
        <template #[`item.source`]="{ item }">
          <v-chip v-if="item.source" size="x-small"
                  :color="item.source.type === 'reclamation' ? '#00838F' : 'primary'" variant="tonal">
            {{ item.source.type === 'reclamation' ? 'Réclamation' : 'Dossier' }} #{{ item.source.id }}
          </v-chip>
          <span v-else class="text-medium-emphasis">—</span>
        </template>
        <template #[`item.affecte_a_nom`]="{ item }">
          <v-chip v-if="item.affecte_a_nom" size="small" variant="tonal"
                  :color="item.affecte_a === monId ? 'primary' : 'grey'"
                  prepend-icon="mdi-account-outline">{{ item.affecte_a_nom }}</v-chip>
          <span v-else class="text-medium-emphasis">—</span>
        </template>
        <template #[`item.statut`]="{ item }">
          <v-chip :color="COULEUR_STATUT[item.statut]" size="small" variant="flat">
            {{ item.statut_libelle }}
          </v-chip>
        </template>
        <template #[`item.cree_le`]="{ item }">{{ dateFr(item.cree_le) }}</template>
        <template #[`item.actions`]="{ item }">
          <v-btn variant="text" color="primary" size="small" append-icon="mdi-arrow-right"
                 @click="ouvrir(item)">Examiner</v-btn>
        </template>
        <template #no-data>
          <div class="text-center py-8 text-medium-emphasis">Aucun recours.</div>
        </template>
      </v-data-table-server>
    </v-card>

    <!-- Détail / traitement -->
    <v-dialog v-model="dialog" max-width="1100" scrollable>
      <v-card v-if="detail" rounded="lg">
        <v-card-title class="d-flex align-center ga-2 pa-4">
          <v-icon color="primary">mdi-gavel</v-icon>
          <span class="text-h6">{{ nomComplet(detail) }}</span>
          <v-spacer />
          <v-chip :color="COULEUR_STATUT[detail.statut]" size="small" variant="flat">{{ detail.statut_libelle }}</v-chip>
        </v-card-title>
        <v-divider />
        <v-card-text class="pa-4">
          <!-- Mode ÉDITION -->
          <template v-if="modeEdition">
            <v-row dense>
              <v-col cols="12" sm="4"><v-text-field v-model="edit.nom" label="Nom *" density="compact" variant="outlined" hide-details /></v-col>
              <v-col cols="12" sm="4"><v-text-field v-model="edit.postnom" label="Postnom" density="compact" variant="outlined" hide-details /></v-col>
              <v-col cols="12" sm="4"><v-text-field v-model="edit.prenom" label="Prénom *" density="compact" variant="outlined" hide-details /></v-col>
            </v-row>
            <v-row dense class="mt-1">
              <v-col cols="12" sm="4"><v-text-field v-model="edit.date_naissance" label="Date de naissance" type="date" density="compact" variant="outlined" hide-details /></v-col>
              <v-col cols="12" sm="4"><v-text-field v-model="edit.cree_le" label="Date de réception" type="date" density="compact" variant="outlined" hide-details /></v-col>
              <v-col cols="12" sm="4"><v-text-field v-model="edit.email" label="Email" type="email" density="compact" variant="outlined" hide-details /></v-col>
            </v-row>
            <v-textarea v-model="edit.message" label="Message" rows="4" variant="outlined" hide-details class="mt-2" />
          </template>

          <!-- Mode LECTURE -->
          <template v-else>
            <v-row>
              <!-- Colonne gauche : le recours + décision -->
              <v-col cols="12" md="5">
                <div class="d-flex ga-4 mb-3 text-body-2 flex-wrap">
                  <span class="dn"><v-icon size="16">mdi-cake-variant-outline</v-icon> Né(e) le {{ dateFr(detail.date_naissance) }}</span>
                  <span v-if="detail.email"><v-icon size="16">mdi-email-outline</v-icon> {{ detail.email }}</span>
                </div>
                <div class="text-caption text-medium-emphasis mb-3">Reçu le {{ dateFr(detail.cree_le) }}</div>
                <div class="mb-3">
                  <span class="text-caption text-medium-emphasis mr-2">Affecté à :</span>
                  <v-chip v-if="detail.affecte_a_nom" size="small" variant="tonal"
                          :color="detail.affecte_a === monId ? 'primary' : 'grey'"
                          prepend-icon="mdi-account-outline">{{ detail.affecte_a_nom }}</v-chip>
                  <span v-else class="text-medium-emphasis">Non affecté</span>
                </div>
                <div class="mb-3">
                  <span class="text-caption text-medium-emphasis mr-2">Recours lié à :</span>
                  <template v-if="detail.source">
                    <v-chip size="small" :color="detail.source.type === 'reclamation' ? '#00838F' : 'primary'" variant="tonal">
                      {{ detail.source.type === 'reclamation' ? 'Réclamation' : 'Dossier' }} #{{ detail.source.id }}
                    </v-chip>
                    <div class="text-body-2 text-medium-emphasis mt-1">
                      {{ [detail.source.poste, detail.source.appel, detail.source.statut].filter(Boolean).join(' · ') }}
                    </div>
                  </template>
                  <span v-else class="text-medium-emphasis">source supprimée</span>
                </div>
                <div class="mb-3">
                  <span class="text-caption text-medium-emphasis mr-2">Domaine retenu :</span>
                  <v-chip size="small" variant="tonal" color="primary" prepend-icon="mdi-briefcase-outline">
                    {{ detail.poste_libelle || 'non précisé' }}
                  </v-chip>
                  <v-chip v-if="detail.poste" size="x-small" variant="flat" color="amber-darken-2" class="ml-1">
                    corrigé
                  </v-chip>
                </div>
                <v-alert type="info" variant="tonal" density="compact" class="mb-3" icon="mdi-card-account-details-outline">
                  Vérifiez la <strong>date de naissance</strong> ci-dessus avec la pièce d'identité du demandeur.
                </v-alert>
                <v-card variant="tonal" color="grey" class="pa-3 mb-4">
                  <div class="text-caption font-weight-bold mb-1">Message du demandeur</div>
                  <div style="white-space: pre-wrap">{{ detail.message }}</div>
                </v-card>

                <v-card v-if="detail.reponse" variant="tonal" color="blue-grey" class="pa-3">
                  <div class="text-caption font-weight-bold mb-1">Note interne / motif</div>
                  <div style="white-space: pre-wrap">{{ detail.reponse }}</div>
                </v-card>
                <div v-if="detail.traite_par" class="text-caption text-medium-emphasis mt-2">
                  {{ detail.statut === 'rejete' ? 'Rejeté' : 'Validé' }} par {{ detail.traite_par }} le {{ dateFr(detail.traite_le) }}
                </div>
              </v-col>

              <!-- Colonne droite : enregistrements & documents de la personne -->
              <v-col cols="12" md="7">
                <div class="d-flex align-center ga-2 mb-2">
                  <v-icon size="18" color="primary">mdi-account-search-outline</v-icon>
                  <span class="text-subtitle-2 font-weight-bold text-primary">Dossiers & réclamations de la personne</span>
                  <v-chip v-if="personne" size="x-small" variant="tonal" color="primary">{{ nbEnregistrements }}</v-chip>
                </div>
                <p class="text-caption text-medium-emphasis mb-3">
                  Tous les enregistrements au même nom (doublons inclus). Cliquez un document pour le visualiser.
                </p>

                <div v-if="chargementPersonne" class="text-center py-6">
                  <v-progress-circular indeterminate color="primary" size="28" />
                </div>
                <template v-else-if="personne">
                  <v-alert v-if="nbEnregistrements === 0" type="warning" variant="tonal" density="compact">
                    Aucun enregistrement retrouvé à ce nom.
                  </v-alert>

                  <!-- Dossiers -->
                  <div v-for="d in personne.dossiers" :key="'d' + d.id" class="enr">
                    <div class="enr-tete">
                      <v-icon size="18" color="#1a237e">mdi-folder-account-outline</v-icon>
                      <span class="font-weight-bold">Dossier #{{ d.id }}</span>
                      <v-chip size="x-small" :color="COULEUR_STATUT_DOSSIER(d.statut)" variant="tonal">{{ d.statut_libelle }}</v-chip>
                      <v-chip v-if="d.est_source" size="x-small" color="error" variant="flat">Source du recours</v-chip>
                      <v-spacer />
                      <span class="text-caption text-medium-emphasis">{{ dateFr(d.cree_le) }}</span>
                    </div>
                    <div class="enr-meta">{{ [d.poste, d.appel].filter(Boolean).join(' · ') }}</div>
                    <div v-if="d.documents.length" class="enr-docs">
                      <v-chip v-for="doc in d.documents" :key="doc.id" size="small" variant="outlined"
                              color="primary" class="ma-1" prepend-icon="mdi-file-eye-outline"
                              @click="voirDocument(doc)">
                        {{ doc.libelle }}
                      </v-chip>
                    </div>
                    <div v-else class="text-caption text-medium-emphasis mt-1">Aucun document.</div>
                    <div v-if="d.motif_rejet" class="motif-rejet">
                      <v-icon size="14" color="error">mdi-information-outline</v-icon>
                      <span><strong>Motif du rejet :</strong> {{ d.motif_rejet }}</span>
                    </div>
                  </div>

                  <!-- Réclamations -->
                  <div v-for="r in personne.reclamations" :key="'r' + r.id" class="enr">
                    <div class="enr-tete">
                      <v-icon size="18" color="#00838F">mdi-account-alert-outline</v-icon>
                      <span class="font-weight-bold">Réclamation #{{ r.id }}</span>
                      <v-chip size="x-small" color="#00838F" variant="tonal">{{ r.statut_libelle }}</v-chip>
                      <v-chip v-if="r.est_source" size="x-small" color="error" variant="flat">Source du recours</v-chip>
                      <v-spacer />
                      <span class="text-caption text-medium-emphasis">{{ dateFr(r.cree_le) }}</span>
                    </div>
                    <div class="enr-meta">{{ [r.poste, r.appel].filter(Boolean).join(' · ') }}</div>
                    <div v-if="r.documents.length" class="enr-docs">
                      <v-chip v-for="doc in r.documents" :key="doc.id" size="small" variant="outlined"
                              color="#00838F" class="ma-1" prepend-icon="mdi-file-eye-outline"
                              @click="voirDocument(doc)">
                        {{ doc.libelle }}
                      </v-chip>
                    </div>
                    <div v-else class="text-caption text-medium-emphasis mt-1">Aucun document.</div>
                    <div v-if="r.motif_rejet" class="motif-rejet">
                      <v-icon size="14" color="error">mdi-information-outline</v-icon>
                      <span><strong>Motif du rejet :</strong> {{ r.motif_rejet }}</span>
                    </div>
                  </div>
                </template>
              </v-col>
            </v-row>
          </template>
        </v-card-text>
        <v-divider />
        <v-card-actions class="pa-3">
          <!-- Actions en mode édition -->
          <template v-if="modeEdition">
            <v-spacer />
            <v-btn variant="text" @click="modeEdition = false">Annuler</v-btn>
            <v-btn color="primary" variant="flat" prepend-icon="mdi-content-save" :loading="enAction" @click="enregistrer">
              Enregistrer
            </v-btn>
          </template>
          <!-- Actions en mode lecture -->
          <template v-else>
            <v-btn v-if="auth.estAdmin" variant="text" prepend-icon="mdi-pencil" @click="ouvrirEdition">
              Modifier
            </v-btn>
            <v-btn v-if="auth.estAdmin" variant="text" prepend-icon="mdi-briefcase-edit-outline" @click="ouvrirDomaine">
              Domaine
            </v-btn>
            <v-btn v-if="auth.peutSuperviser && detail.statut !== 'en_attente'" variant="text"
                   prepend-icon="mdi-lock-open-variant-outline" :loading="enAction" @click="rouvrir">
              Rouvrir
            </v-btn>
            <v-spacer />
            <v-btn variant="text" @click="dialog = false">Fermer</v-btn>
            <!-- Décision : agent affecté (ou admin/superviseur) -->
            <span v-if="auth.peutTraiter && !peutDecider(detail)" class="text-caption text-medium-emphasis mr-2">
              Affecté à un autre agent
            </span>
            <template v-if="peutDecider(detail) && detail.statut !== 'rejete'">
              <v-btn color="error" variant="tonal" prepend-icon="mdi-close-circle-outline"
                     :loading="enAction" @click="demanderDecision('rejeter')">Rejeter</v-btn>
            </template>
            <template v-if="peutDecider(detail) && detail.statut !== 'valide'">
              <v-btn color="success" variant="flat" prepend-icon="mdi-check-decagram-outline"
                     :loading="enAction" @click="demanderDecision('valider')">Valider</v-btn>
            </template>
          </template>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Mise à jour du domaine (poste) — admin -->
    <v-dialog v-model="dialogDomaine" max-width="480">
      <v-card v-if="detail" rounded="lg">
        <v-card-title class="d-flex align-center ga-2 pa-4">
          <v-icon color="primary">mdi-briefcase-edit-outline</v-icon>
          <span class="text-h6">Domaine du recours</span>
        </v-card-title>
        <v-divider />
        <v-card-text class="pa-4">
          <p class="text-body-2 text-medium-emphasis mb-3">
            Domaine retenu pour <strong>{{ nomComplet(detail) }}</strong>.
            C'est ce domaine qui figurera sur la liste définitive si le recours est validé.
          </p>
          <v-select v-model="domaineChoisi" :items="postes" item-title="libelle" item-value="id"
                    label="Domaine (poste)" density="comfortable" variant="outlined"
                    clearable hide-details />
          <p class="text-caption text-medium-emphasis mt-2">
            Laisser vide = reprendre le domaine de l'enregistrement source
            <template v-if="detail.source"> ({{ detail.source.poste || 'non précisé' }})</template>.
          </p>
        </v-card-text>
        <v-divider />
        <v-card-actions class="pa-3">
          <v-spacer />
          <v-btn variant="text" @click="dialogDomaine = false">Annuler</v-btn>
          <v-btn color="primary" variant="flat" prepend-icon="mdi-content-save"
                 :loading="enAction" @click="majDomaine">Enregistrer</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Confirmation de décision (vert = valider, rouge = rejeter) -->
    <v-dialog v-model="confirme.show" max-width="460">
      <v-card rounded="lg" :class="confirme.type === 'valider' ? 'confirm-valider' : 'confirm-rejeter'">
        <div class="confirm-tete">
          <v-icon :color="confirme.type === 'valider' ? '#2E7D32' : '#C62828'" size="26">
            {{ confirme.type === 'valider' ? 'mdi-check-decagram' : 'mdi-close-circle' }}
          </v-icon>
          <span class="text-h6 font-weight-bold">
            {{ confirme.type === 'valider' ? 'Valider le recours ?' : 'Rejeter le recours ?' }}
          </span>
        </div>
        <v-card-text class="pb-2 pt-4">
          <template v-if="confirme.type === 'valider'">
            La personne sera ajoutée à la liste interne des <strong>validés après recours</strong>.
            Cela <strong>n'actualise pas</strong> la liste publique des retenus : la publication
            définitive reste une étape ultérieure.
          </template>
          <template v-else>
            Le recours de <strong>{{ nomComplet(detail || {}) }}</strong> sera marqué
            <strong>rejeté</strong> (décision défavorable). Vous pourrez le rouvrir si besoin.
          </template>

          <v-textarea v-model="reponse" class="mt-4" rows="3" variant="outlined"
                      :color="confirme.type === 'valider' ? 'success' : 'error'"
                      :label="confirme.type === 'rejeter' ? 'Motif du rejet *' : 'Note interne (facultatif)'"
                      :error-messages="erreurNote"
                      @update:model-value="erreurNote = ''" />
        </v-card-text>
        <v-card-actions class="pa-3">
          <v-spacer />
          <v-btn variant="text" @click="confirme.show = false">Annuler</v-btn>
          <v-btn :color="confirme.type === 'valider' ? 'success' : 'error'" variant="flat"
                 :prepend-icon="confirme.type === 'valider' ? 'mdi-check-decagram-outline' : 'mdi-close-circle-outline'"
                 :loading="enAction" @click="confirmerDecision">
            {{ confirme.type === 'valider' ? 'Confirmer la validation' : 'Confirmer le rejet' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Aperçu de document (image : rotation / zoom ; PDF : iframe) -->
    <v-dialog v-model="apercu.show" max-width="1000" scrollable>
      <v-card rounded="lg">
        <v-card-title class="d-flex align-center ga-1 pa-2 pl-3">
          <v-icon color="primary" class="mr-1">mdi-file-eye-outline</v-icon>
          <span class="text-subtitle-1 text-truncate" style="max-width: 240px">{{ apercu.titre }}</span>
          <v-spacer />
          <!-- Outils image : rotation + zoom -->
          <template v-if="apercu.estImage">
            <v-btn icon="mdi-rotate-left" variant="text" size="small" title="Pivoter à gauche" @click="pivoter(-1)" />
            <v-btn icon="mdi-rotate-right" variant="text" size="small" title="Pivoter à droite" @click="pivoter(1)" />
            <v-btn icon="mdi-magnify-minus-outline" variant="text" size="small" title="Dézoomer" @click="zoomer(-0.25)" />
            <span class="text-caption" style="min-width: 38px; text-align:center">{{ Math.round(zoom * 100) }}%</span>
            <v-btn icon="mdi-magnify-plus-outline" variant="text" size="small" title="Zoomer" @click="zoomer(0.25)" />
            <v-btn icon="mdi-backup-restore" variant="text" size="small" title="Réinitialiser" @click="reinitVue" />
            <v-divider vertical class="mx-1" />
          </template>
          <v-btn icon="mdi-download" variant="text" size="small" title="Télécharger"
                 :href="apercu.urlDl" />
          <v-btn icon="mdi-open-in-new" variant="text" size="small" title="Ouvrir dans un onglet"
                 :href="apercu.url" target="_blank" />
          <v-btn icon="mdi-close" variant="text" size="small" @click="apercu.show = false" />
        </v-card-title>
        <v-divider />
        <v-card-text class="pa-0">
          <div v-if="apercu.estImage" class="apercu-img-zone">
            <img :src="apercu.url" :style="styleImage" class="apercu-img" alt="aperçu" />
          </div>
          <iframe v-else-if="apercu.url" :src="apercu.url" title="Aperçu" class="apercu-frame" />
        </v-card-text>
      </v-card>
    </v-dialog>

    <!-- Répartition de la charge entre agents (supervision) -->
    <v-dialog v-model="dialogRepartir" max-width="560">
      <v-card flat border rounded="lg">
        <v-card-title class="d-flex align-center ga-2 py-4">
          <v-icon color="primary">mdi-account-multiple-check-outline</v-icon>
          <span class="font-weight-bold">Répartir les recours</span>
        </v-card-title>
        <v-divider />
        <v-card-text>
          <v-alert type="info" variant="tonal" density="compact" class="mb-3">
            Catégorie répartie :
            <strong>{{ statut === 'valide' ? 'Validés' : statut === 'rejete' ? 'Rejetés' : 'En attente' }}</strong>
            <span v-if="q"> · recherche « {{ q }} »</span>.
            Distribution <strong>équitable</strong> entre les agents. Les recours d'une
            <strong>même personne</strong> (doublons) restent assignés au même agent.
            <template v-if="reequilibrer"> <strong>Rééquilibrage</strong> : les déjà affectés sont aussi redistribués.</template>
            <template v-else> Les déjà affectés ne sont pas touchés.</template>
          </v-alert>
          <v-alert v-if="categorieDecidee" type="warning" variant="tonal" density="compact" class="mb-3"
                   icon="mdi-shield-account-outline">
            Catégorie déjà décidée : seuls les <strong>superviseurs</strong> peuvent être affectés (révision).
          </v-alert>
          <v-switch v-model="reequilibrer" color="primary" density="compact" hide-details class="mb-1"
                    label="Rééquilibrer (réaffecter aussi les déjà affectés)" />
          <v-select v-model="agentsChoisis" :items="agentsEligibles" item-title="nom" item-value="id"
                    label="Agents" multiple chips closable-chips
                    prepend-inner-icon="mdi-account-group-outline"
                    :hint="categorieDecidee ? 'Superviseurs uniquement pour cette catégorie.' : 'Agents qui traiteront ces recours.'"
                    persistent-hint />

          <div v-if="resultatRepartition" class="mt-4">
            <v-divider class="mb-3" />
            <div class="font-weight-bold mb-2">
              {{ resultatRepartition.total_reparti }} recours
              <span v-if="resultatRepartition.personnes != null">({{ resultatRepartition.personnes }} personne(s))</span>
              réparti(s) :
            </div>
            <div v-for="p in resultatRepartition.par_agent" :key="p.agent_id"
                 class="d-flex align-center justify-space-between py-1">
              <span><v-icon size="18" class="mr-1">mdi-account</v-icon>{{ p.agent }}</span>
              <v-chip size="small" color="primary" variant="tonal">{{ p.attribues }}</v-chip>
            </div>
          </div>
        </v-card-text>
        <v-card-actions class="px-4 pb-4">
          <v-btn variant="text" @click="dialogRepartir = false">Fermer</v-btn>
          <v-spacer />
          <v-btn color="primary" variant="flat" :loading="enRepartition"
                 :disabled="!agentsChoisis.length" @click="repartir">
            Répartir maintenant
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snack.show" :color="snack.color" timeout="3000">{{ snack.text }}</v-snackbar>
  </div>
</template>

<style scoped>
.dn { font-weight: 600; color: #1a237e; }
.motif-rejet { display: flex; align-items: flex-start; gap: 6px; margin-top: 8px; padding: 7px 10px;
  background: #fdecea; border-radius: 8px; font-size: 0.82rem; color: #8b2c26; line-height: 1.4; }
.enr { border: 1px solid #e0e3ee; border-radius: 12px; padding: 10px 12px; margin-bottom: 10px; background: #fafbff; }
.enr-tete { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.enr-meta { font-size: 0.82rem; color: #66707e; margin: 2px 0 4px; }
.enr-docs { display: flex; flex-wrap: wrap; margin: 2px -4px 0; }
.apercu-frame { width: 100%; height: 72vh; border: 0; }
.apercu-img-zone { height: 72vh; display: flex; align-items: center; justify-content: center;
  overflow: auto; background: #2b2b33; padding: 12px; }
.apercu-img { max-width: 100%; max-height: 100%; object-fit: contain; transition: transform 0.2s ease;
  box-shadow: 0 4px 24px rgba(0,0,0,0.35); background: #fff; }
.confirm-tete { display: flex; align-items: center; gap: 10px; padding: 16px 20px; }
.confirm-valider { border-top: 4px solid #2E7D32; }
.confirm-valider .confirm-tete { background: #E8F5E9; color: #1B5E20; }
.confirm-rejeter { border-top: 4px solid #C62828; }
.confirm-rejeter .confirm-tete { background: #FDECEA; color: #8B2C26; }
</style>
