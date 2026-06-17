<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import api from '../../api'
import StatCard from '../../components/StatCard.vue'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
// Peut traiter (valider/rejeter) une réclamation : admin, superviseur ou validateur.
const peutTraiter = computed(() => auth.peutTraiter)
const monId = computed(() => auth.utilisateur?.id)
// Décision sur une réclamation précise : un admin peut toujours ; un validateur
// seulement si elle LUI est affectée (cohérent avec le contrôle serveur).
function peutDecider(item) {
  if (auth.peutSuperviser) return true
  return auth.estValidateur && item?.affecte_a === monId.value
}

const reclamations = ref([])
const total = ref(0)
const chargement = ref(false)

// Filtres mémorisés (localStorage) : retrouvés au retour sur la page, pour ne
// pas refiltrer après avoir traité une réclamation. Survit au rechargement.
// Clé SUFFIXÉE par l'id de l'utilisateur connecté : filtres propres à chaque
// compte, sans fuite d'une session à l'autre sur la même machine.
const STORAGE_FILTRES = `acgt_filtres_reclamations_${auth.utilisateur?.id ?? 'anon'}`
function filtresSauvegardes() {
  try { return JSON.parse(localStorage.getItem(STORAGE_FILTRES)) || {} } catch { return {} }
}
const sauve = filtresSauvegardes()

const statut = ref(sauve.statut ?? 'en_attente')
const appel = ref(sauve.appel ?? null)
const q = ref(sauve.q ?? '')
const dossierDepose = ref(sauve.dossierDepose ?? false)
// Filtre d'affectation. Un validateur (non admin) voit par défaut SON lot ;
// un admin voit tout. '' = tous, 'moi' = mon lot, 'aucune' = non affectées,
// '<id>' = le lot d'un agent (admin seulement).
const affecteParDefaut = (auth.estValidateur && !auth.estAdmin) ? 'moi' : ''
const affecte = ref(sauve.affecte ?? affecteParDefaut)

watch([statut, appel, q, dossierDepose, affecte], () => {
  localStorage.setItem(STORAGE_FILTRES, JSON.stringify({
    statut: statut.value, appel: appel.value, q: q.value,
    dossierDepose: dossierDepose.value, affecte: affecte.value,
  }))
})

// Options du filtre « affecté à ».
const optionsAffecte = computed(() => {
  if (!auth.peutSuperviser) {
    return [{ value: 'moi', title: 'Les miennes' }, { value: '', title: 'Toutes' }]
  }
  return [
    { value: '', title: 'Tous les agents' },
    { value: 'moi', title: 'Les miennes' },
    { value: 'aucune', title: 'Non affectées' },
    ...agents.value.map((a) => ({ value: String(a.id), title: a.nom })),
  ]
})
const appels = ref([])
const postes = ref([])
const agents = ref([])           // agents pouvant traiter (admin/validateur)
const stats = ref({ total: 0, par_statut: {} })
const snack = ref({ show: false, color: 'success', text: '' })

// Répartition de la charge (admin)
const dialogRepartir = ref(false)
const agentsChoisis = ref([])
const enRepartition = ref(false)
const resultatRepartition = ref(null)
const reequilibrer = ref(false)   // réaffecter aussi les déjà affectées
// Catégorie déjà décidée (validées / rejetées) : révision réservée aux
// superviseurs. « En attente » (et défaut) : agents de traitement.
const categorieDecidee = computed(() => !['', 'en_attente'].includes(statut.value))
// Agents proposés selon la catégorie filtrée.
const agentsEligibles = computed(() => agents.value.filter((a) =>
  categorieDecidee.value
    ? (a.roles.includes('admin') || a.roles.includes('superviseur'))
    : true))

// Détail / décision
const detail = ref(null)
const dialog = ref(false)
const posteChoisi = ref(null)
const motifRejet = ref('')
const action = ref(null)         // 'valider' | 'rejeter'
const enCours = ref(false)

// Grille de critères (cases à cocher à la validation)
const criteres = ref([])           // critères actifs (portée réclamation)
const criteresCoches = ref([])     // ids cochés pour la réclamation courante
const derogation = ref('')         // justification admin si critères manquants
const criteresManquants = computed(() =>
  criteres.value.filter((c) => !criteresCoches.value.includes(c.id)))
// Validation possible : tous cochés, ou admin avec dérogation justifiée.
const grilleSatisfaite = computed(() =>
  criteresManquants.value.length === 0
  || (auth.estAdmin && derogation.value.trim().length > 0))

const KPIS = [
  { key: '', label: 'Total', desc: 'Toutes', icon: 'mdi-account-alert-outline', color: '#1a237e' },
  { key: 'en_attente', label: 'En attente', desc: 'À traiter', icon: 'mdi-clock-outline', color: '#EF6C00' },
  { key: 'validee', label: 'Validées', desc: 'Retenues', icon: 'mdi-check-circle', color: '#2E7D32' },
  { key: 'rejetee', label: 'Rejetées', desc: 'Refusées', icon: 'mdi-close-circle', color: '#C62828' },
]
const compte = (k) => (k === '' ? stats.value.total : stats.value.par_statut[k] || 0)
const COULEUR = { en_attente: 'warning', validee: 'success', rejetee: 'error' }
// Couleurs des statuts de DOSSIER (pour les dossiers liés affichés ici).
const COULEUR_DOSSIER = {
  brouillon: 'grey', depose: 'warning', en_examen: 'info',
  retenu: 'success', non_retenu: 'blue-grey', rejete: 'error',
}

const ENTETES = [
  { title: '#', key: 'id', width: 60, sortable: false },
  { title: 'Personne', key: 'personne', sortable: false },
  { title: 'Appel', key: 'appel_titre', sortable: false },
  { title: 'Contact', key: 'email', sortable: false },
  { title: 'Affecté à', key: 'affecte_a_nom', sortable: false },
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
const cle = computed(() => `${statut.value}|${appel.value || ''}|${dossierDepose.value}|${affecte.value}|${q.value}`)

async function charger({ page = 1, itemsPerPage = 25 } = {}) {
  chargement.value = true
  try {
    const params = { page, page_size: itemsPerPage > 0 ? itemsPerPage : 25 }
    if (statut.value) params.statut = statut.value
    if (appel.value) params.appel = appel.value
    if (dossierDepose.value) params.dossier_depose = 1
    if (affecte.value) params.affecte = affecte.value
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
const docsDoublonOuverts = ref([])   // ids des doublons dont on affiche les justificatifs
function basculerDocsDoublon(id) {
  docsDoublonOuverts.value = docsDoublonOuverts.value.includes(id)
    ? docsDoublonOuverts.value.filter((x) => x !== id)
    : [...docsDoublonOuverts.value, id]
}
const dossiersDeposes = ref([])
const rejetDossierEnCours = ref(false)
const dossierLieEnCours = ref(null)
const docsDossierOuverts = ref([])   // ids des dossiers liés dont on affiche les pièces
function basculerDocsDossier(id) {
  docsDossierOuverts.value = docsDossierOuverts.value.includes(id)
    ? docsDossierOuverts.value.filter((x) => x !== id)
    : [...docsDossierOuverts.value, id]
}
// Téléchargement protégé d'une pièce de dossier (même origine via le proxy).
const lienPiece = (dossierId, pieceId) => `/api/dossiers/${dossierId}/pieces/${pieceId}/telecharger/`
async function ouvrir(rec) {
  detail.value = rec
  action.value = null
  // Pré-sélectionne le poste déclaré par le réclamant (absent sur les
  // anciennes réclamations) ; l'admin peut le changer avant de valider.
  posteChoisi.value = rec.poste || null
  motifRejet.value = ''
  criteresCoches.value = []        // grille remise à zéro à chaque ouverture
  derogation.value = ''
  doublonsRec.value = []
  docsDoublonOuverts.value = []
  dossiersDeposes.value = []
  docsDossierOuverts.value = []
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

// Rejet du DOSSIER lié (et non de la réclamation) — utile si c'est le dossier
// qui fait doublon. Le serveur applique le verrou d'affectation (admin, ou
// validateur affecté à ce dossier). La réclamation en cours n'est pas touchée.
async function rejeterDossierLie(d) {
  if (!confirm(`Rejeter le dossier ${d.code || '#' + d.id} de ${d.nom} ${d.prenom} ? `
    + 'La réclamation en cours reste ouverte. Aucun email ne sera envoyé.')) return
  dossierLieEnCours.value = d.id
  try {
    await api.post(`/dossiers/${d.id}/rejeter/`, { motif: 'Dossier en double (réclamation en parallèle)' })
    notifier('Dossier lié rejeté.')
    // Met à jour l'affichage local du dossier (statut → rejeté, bouton retiré).
    dossiersDeposes.value = dossiersDeposes.value.map((x) =>
      x.id === d.id ? { ...x, statut: 'rejete', statut_libelle: 'Rejeté' } : x)
  } catch (e) {
    notifier(e.response?.data?.detail || e.response?.data?.motif?.[0] || 'Rejet impossible.', 'error')
  } finally {
    dossierLieEnCours.value = null
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

// Ouvre une réclamation (un doublon, p. ex.) dans la fiche pour l'examiner
// — justificatifs compris — avant de décider de la rejeter.
async function examinerReclamation(id) {
  try {
    const { data } = await api.get(`/reclamations/${id}/`)
    await ouvrir(data)
  } catch {
    notifier("Impossible d'ouvrir cette réclamation.", 'error')
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

// Répartit équitablement la catégorie filtrée entre les agents choisis.
// Rééquilibrage possible (réaffecte aussi les déjà affectées).
async function repartir() {
  if (!agentsChoisis.value.length) {
    notifier('Sélectionnez au moins un agent.', 'error'); return
  }
  enRepartition.value = true
  resultatRepartition.value = null
  try {
    const corps = {
      agents: agentsChoisis.value,
      seulement_non_affectees: !reequilibrer.value,
    }
    if (statut.value) corps.statut = statut.value
    if (appel.value) corps.appel = appel.value
    if (q.value) corps.q = q.value
    const { data } = await api.post('/reclamations/repartir/', corps)
    resultatRepartition.value = data
    notifier(`${data.total_reparti} réclamation(s) réparties entre ${data.par_agent.length} agent(s).`)
    await Promise.all([charger(), chargerStats()])
  } catch (e) {
    notifier(e.response?.data?.agents || e.response?.data?.detail || 'Répartition impossible.', 'error')
  } finally {
    enRepartition.value = false
  }
}

async function confirmer() {
  enCours.value = true
  try {
    if (action.value === 'valider') {
      if (!grilleSatisfaite.value) {
        notifier('Cochez tous les critères (ou justifiez une dérogation).', 'error')
        enCours.value = false; return
      }
      const corps = { criteres: criteresCoches.value }
      if (posteChoisi.value) corps.poste_id = posteChoisi.value
      if (derogation.value.trim()) corps.derogation = derogation.value.trim()
      await api.post(`/reclamations/${detail.value.id}/valider/`, corps)
      notifier('Réclamation validée — la personne est désormais retenue.')
    } else {
      if (!motifRejet.value.trim()) { notifier('Le motif est obligatoire.', 'error'); enCours.value = false; return }
      await api.post(`/reclamations/${detail.value.id}/rejeter/`,
        { motif: motifRejet.value, criteres: criteresCoches.value })
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
  // Liste des agents pouvant traiter (pour répartir / filtrer) — admin seulement.
  if (auth.peutSuperviser) {
    try {
      const { data } = await api.get('/auth/utilisateurs/')
      agents.value = data
        .filter((u) => u.roles.includes('admin') || u.roles.includes('superviseur')
          || u.roles.includes('validateur'))
        .map((u) => ({ id: u.id, nom: `${u.prenom} ${u.nom}`.trim() || u.email, roles: u.roles }))
    } catch { /* non bloquant */ }
  }
  // Grille de critères actifs (portée réclamation) pour la validation.
  try {
    criteres.value = (await api.get('/criteres/', { params: { portee: 'reclamation' } })).data
  } catch { /* non bloquant */ }
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
      <v-select v-model="affecte" :items="optionsAffecte" label="Affecté à" hide-details density="compact"
                variant="outlined" prepend-inner-icon="mdi-account-arrow-right-outline" style="max-width: 200px" />
      <v-btn :variant="dossierDepose ? 'flat' : 'outlined'" :color="dossierDepose ? 'deep-orange' : 'grey'"
             prepend-icon="mdi-folder-account-outline" @click="dossierDepose = !dossierDepose">
        A déjà un dossier
      </v-btn>
      <v-btn v-if="auth.peutSuperviser" color="primary" variant="flat"
             prepend-icon="mdi-account-multiple-check-outline" @click="dialogRepartir = true">
        Répartir
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
        <template #item.affecte_a_nom="{ item }">
          <v-chip v-if="item.affecte_a_nom" size="small" variant="tonal"
                  :color="item.affecte_a === monId ? 'primary' : 'grey'"
                  prepend-icon="mdi-account-outline">{{ item.affecte_a_nom }}</v-chip>
          <span v-else class="text-medium-emphasis">—</span>
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
          <div class="info-l"><span>Affecté à</span><strong>{{ detail.affecte_a_nom || 'Non affectée' }}</strong></div>

          <!-- Doublons : autres réclamations de la même personne -->
          <v-alert v-if="doublonsRec.length" type="warning" variant="tonal" density="compact"
                   class="mt-3" icon="mdi-content-duplicate">
            <div class="font-weight-bold mb-1">
              {{ doublonsRec.length }} autre(s) réclamation(s) de cette personne (même nom).
            </div>
            <div v-for="r in doublonsRec" :key="r.id" class="doublon-bloc mt-1">
              <div class="d-flex align-center flex-wrap ga-2">
                <v-chip :color="COULEUR[r.statut]" size="x-small" variant="flat" label>{{ r.statut_libelle }}</v-chip>
                <span class="text-caption flex-grow-1" style="min-width:0">
                  <strong>{{ r.nom }} {{ r.postnom }} {{ r.prenom }}</strong>
                  <span class="text-medium-emphasis"> · #{{ r.id }} · {{ r.email }}</span>
                </span>
                <v-btn size="x-small" color="primary" variant="text"
                       :prepend-icon="docsDoublonOuverts.includes(r.id) ? 'mdi-chevron-up' : 'mdi-paperclip'"
                       @click="basculerDocsDoublon(r.id)">
                  Documents ({{ r.documents?.length || 0 }})
                </v-btn>
                <v-btn size="x-small" color="primary" variant="text" prepend-icon="mdi-eye-outline"
                       @click="examinerReclamation(r.id)">Examiner</v-btn>
                <v-btn v-if="peutTraiter && r.statut === 'en_attente'" size="x-small" color="error" variant="tonal"
                       :loading="doublonEnCours === r.id" @click="rejeterDoublonRec(r)">
                  Rejeter le doublon
                </v-btn>
              </div>
              <!-- Justificatifs du doublon (dépliable) : pour vérifier avant de rejeter -->
              <v-expand-transition>
                <div v-show="docsDoublonOuverts.includes(r.id)" class="mt-1">
                  <div v-if="!r.documents?.length" class="text-caption text-medium-emphasis pl-2">
                    Aucun justificatif joint.
                  </div>
                  <div v-for="doc in r.documents" :key="doc.id" class="doc-l">
                    <v-icon size="18" color="primary" class="mr-2">{{ ICONE_DOC[doc.type] || 'mdi-file' }}</v-icon>
                    <span class="flex-grow-1" style="min-width:0">
                      <strong>{{ doc.type_libelle }}</strong>
                      <span class="text-medium-emphasis"> — {{ doc.nom_original }} · {{ kos(doc.taille) }}</span>
                    </span>
                    <a :href="`${lienDoc(r.id, doc.id)}?inline=1`" target="_blank" @click.stop>
                      <v-btn icon="mdi-eye-outline" variant="text" size="x-small" color="primary" />
                    </a>
                    <a :href="lienDoc(r.id, doc.id)" target="_blank" @click.stop>
                      <v-btn icon="mdi-download" variant="text" size="x-small" color="primary" />
                    </a>
                  </div>
                </div>
              </v-expand-transition>
            </div>
          </v-alert>

          <!-- Croisement : la personne a déjà un dossier déposé -->
          <v-alert v-if="dossiersDeposes.length" type="error" variant="tonal" density="compact"
                   class="mt-3" icon="mdi-folder-account-outline">
            <div class="font-weight-bold mb-1">
              Cette personne a déjà {{ dossiersDeposes.length }} dossier(s) déposé(s) — elle est
              déjà candidate. Cette réclamation est probablement redondante.
            </div>
            <div v-for="d in dossiersDeposes" :key="d.id" class="doublon-bloc mt-1">
              <div class="d-flex align-center flex-wrap ga-2">
                <RouterLink :to="{ name: 'dossier', params: { id: d.id } }" class="font-weight-bold lien-dossier">
                  {{ d.code || ('#' + d.id) }}
                </RouterLink>
                <v-chip :color="COULEUR_DOSSIER[d.statut] || 'grey'" size="x-small" variant="flat" label>
                  {{ d.statut_libelle }}
                </v-chip>
                <span class="text-caption flex-grow-1" style="min-width:0">
                  <strong>{{ d.nom }} {{ d.postnom }} {{ d.prenom }}</strong>
                  <span class="text-medium-emphasis"> · {{ d.poste_libelle || d.appel_titre }}</span>
                  <span v-if="d.affecte_a_nom" class="text-medium-emphasis"> · affecté à {{ d.affecte_a_nom }}</span>
                </span>
                <v-btn size="x-small" color="primary" variant="text"
                       :prepend-icon="docsDossierOuverts.includes(d.id) ? 'mdi-chevron-up' : 'mdi-paperclip'"
                       @click="basculerDocsDossier(d.id)">
                  Documents ({{ d.pieces?.length || 0 }})
                </v-btn>
                <!-- Rejeter le DOSSIER lié (et non la réclamation) -->
                <v-btn v-if="d.statut === 'depose' && (auth.peutSuperviser || (auth.estValidateur && d.affecte_a === monId))"
                       size="x-small" color="error" variant="tonal" prepend-icon="mdi-folder-remove-outline"
                       :loading="dossierLieEnCours === d.id" @click="rejeterDossierLie(d)">
                  Rejeter ce dossier
                </v-btn>
              </div>
              <!-- Pièces du dossier (dépliable) : pour décider sans ouvrir le dossier -->
              <v-expand-transition>
                <div v-show="docsDossierOuverts.includes(d.id)" class="mt-1">
                  <div v-if="!d.pieces?.length" class="text-caption text-medium-emphasis pl-2">
                    Aucune pièce jointe.
                  </div>
                  <div v-for="p in d.pieces" :key="p.id" class="doc-l">
                    <v-icon size="18" color="primary" class="mr-2">mdi-file-document-outline</v-icon>
                    <span class="flex-grow-1" style="min-width:0">
                      <strong>{{ p.type_libelle }}</strong>
                      <span class="text-medium-emphasis"> — {{ p.nom_original }} · {{ kos(p.taille) }}</span>
                    </span>
                    <a :href="`${lienPiece(d.id, p.id)}?inline=1`" target="_blank" @click.stop>
                      <v-btn icon="mdi-eye-outline" variant="text" size="x-small" color="primary" />
                    </a>
                    <a :href="lienPiece(d.id, p.id)" target="_blank" @click.stop>
                      <v-btn icon="mdi-download" variant="text" size="x-small" color="primary" />
                    </a>
                  </div>
                </div>
              </v-expand-transition>
            </div>
            <!-- Rejeter la RÉCLAMATION en cours (redondante car déjà candidate) -->
            <v-btn v-if="peutDecider(detail) && detail.statut === 'en_attente'" size="small" color="error" variant="flat"
                   class="mt-3" prepend-icon="mdi-close-circle-outline"
                   :loading="rejetDossierEnCours" @click="rejeterCarDossier">
              Rejeter cette réclamation
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

          <!-- Réclamation affectée à un autre agent : consultation seule -->
          <v-alert v-if="detail.statut === 'en_attente' && peutTraiter && !peutDecider(detail)"
                   type="info" variant="tonal" density="compact" class="mt-4"
                   icon="mdi-account-lock-outline">
            Cette réclamation est affectée à <strong>{{ detail.affecte_a_nom }}</strong>.
            Seul l'agent affecté (ou un administrateur) peut la traiter.
          </v-alert>

          <template v-if="detail.statut === 'en_attente' && peutDecider(detail)">
            <v-divider class="my-4" />

            <!-- Grille de critères (commune) : ce que la personne a / n'a pas -->
            <template v-if="criteres.length">
              <div class="text-caption font-weight-bold text-medium-emphasis mb-1">
                Grille de critères — cochez ce que la personne remplit
              </div>
              <v-checkbox v-for="c in criteres" :key="c.id" v-model="criteresCoches" :value="c.id"
                          :label="c.libelle" density="compact" hide-details color="success" />
              <div class="text-caption text-medium-emphasis mb-3">
                Coché = rempli · non coché = manquant. Enregistré quelle que soit la décision.
              </div>
            </template>

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
              <!-- Critères manquants : blocage (ou dérogation admin) -->
              <template v-if="criteresManquants.length">
                <v-alert v-if="!auth.estAdmin" type="warning" variant="tonal" density="compact" class="mb-2">
                  Cochez tous les critères pour valider (sinon un administrateur peut accorder une dérogation).
                </v-alert>
                <template v-else>
                  <v-alert type="warning" variant="tonal" density="compact" class="mb-2">
                    {{ criteresManquants.length }} critère(s) non rempli(s). En tant qu'administrateur,
                    vous pouvez valider <strong>par dérogation</strong> en justifiant ci-dessous.
                  </v-alert>
                  <v-textarea v-model="derogation" label="Justification de la dérogation (obligatoire)"
                              rows="2" hide-details />
                </template>
              </template>
              <v-select v-model="posteChoisi" :items="postes" label="Poste visé" clearable class="mt-3"
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
            <!-- Réclamation rejetée : motif bien visible en rouge -->
            <v-alert v-if="detail.statut === 'rejetee'" type="error" variant="tonal"
                     density="compact" border="start" icon="mdi-cancel" class="mb-3">
              <div class="font-weight-bold">Réclamation rejetée</div>
              <div v-if="detail.motif" class="mt-1">
                <span class="font-weight-medium">Motif :</span> {{ detail.motif }}
              </div>
              <div v-else class="mt-1 text-medium-emphasis">Aucun motif enregistré.</div>
            </v-alert>
            <div v-else-if="detail.motif" class="info-l"><span>Motif</span><strong>{{ detail.motif }}</strong></div>
            <div class="info-l"><span>Traité par</span><strong>{{ detail.traite_par || '—' }}</strong></div>
            <!-- Grille de critères telle que cochée à la décision -->
            <div v-if="detail.controles?.length" class="mt-3">
              <div class="text-caption font-weight-bold text-medium-emphasis mb-1">Grille de validation</div>
              <div v-for="ctrl in detail.controles" :key="ctrl.id" class="d-flex align-center ga-2 py-1">
                <v-icon size="18" :color="ctrl.rempli ? 'success' : 'error'">
                  {{ ctrl.rempli ? 'mdi-check-circle' : 'mdi-close-circle' }}
                </v-icon>
                <span class="text-body-2">{{ ctrl.libelle_snapshot }}</span>
              </div>
            </div>
          </template>
        </v-card-text>
        <v-card-actions class="px-4 pb-4">
          <v-btn variant="text" @click="dialog = false">Fermer</v-btn>
          <v-btn v-if="detail.a_doublon" variant="tonal" color="warning" size="small"
                 prepend-icon="mdi-content-duplicate" append-icon="mdi-arrow-right"
                 :loading="enNavRec" @click="doublonSuivantRec">Doublon suivant</v-btn>
          <v-spacer />
          <v-btn v-if="action === 'valider'" color="success" variant="flat" :loading="enCours"
                 :disabled="!grilleSatisfaite" @click="confirmer">
            Confirmer la validation
          </v-btn>
          <v-btn v-else-if="action === 'rejeter'" color="error" variant="flat" :loading="enCours" @click="confirmer">
            Confirmer le rejet
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Répartition de la charge entre agents (admin) -->
    <v-dialog v-model="dialogRepartir" max-width="560">
      <v-card flat border rounded="lg">
        <v-card-title class="d-flex align-center ga-2 py-4">
          <v-icon color="primary">mdi-account-multiple-check-outline</v-icon>
          <span class="font-weight-bold">Répartir les réclamations</span>
        </v-card-title>
        <v-divider />
        <v-card-text>
          <v-alert type="info" variant="tonal" density="compact" class="mb-3">
            Catégorie répartie :
            <strong>{{ (KPIS.find((k) => k.key === statut) || {}).label || 'En attente' }}</strong>
            <span v-if="appel"> · appel sélectionné</span><span v-if="q"> · recherche « {{ q }} »</span>.
            Distribution <strong>équitable</strong> entre les agents.
            <template v-if="reequilibrer"> <strong>Rééquilibrage</strong> : les déjà affectées sont aussi redistribuées.</template>
            <template v-else> Les déjà affectées ne sont pas touchées.</template>
          </v-alert>
          <!-- Catégorie décidée : révision réservée aux superviseurs -->
          <v-alert v-if="categorieDecidee" type="warning" variant="tonal" density="compact" class="mb-3"
                   icon="mdi-shield-account-outline">
            Catégorie déjà décidée : seuls les <strong>superviseurs</strong> peuvent être affectés (révision).
          </v-alert>
          <v-switch v-model="reequilibrer" color="primary" density="compact" hide-details class="mb-1"
                    label="Rééquilibrer (réaffecter aussi les déjà affectées)" />
          <v-select v-model="agentsChoisis" :items="agentsEligibles" item-title="nom" item-value="id"
                    label="Agents" multiple chips closable-chips
                    prepend-inner-icon="mdi-account-group-outline"
                    :hint="categorieDecidee ? 'Superviseurs uniquement pour cette catégorie.' : 'Agents qui traiteront ces réclamations.'"
                    persistent-hint />

          <!-- Résultat de la dernière répartition -->
          <div v-if="resultatRepartition" class="mt-4">
            <v-divider class="mb-3" />
            <div class="font-weight-bold mb-2">
              {{ resultatRepartition.total_reparti }} réclamation(s) réparties :
            </div>
            <div v-for="p in resultatRepartition.par_agent" :key="p.agent_id"
                 class="d-flex align-center justify-space-between py-1">
              <span><v-icon size="18" class="mr-1">mdi-account</v-icon>{{ p.agent }}</span>
              <v-chip size="small" color="primary" variant="tonal">{{ p.attribuees }}</v-chip>
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
.doublon-bloc { padding-top: 6px; }
.doublon-bloc + .doublon-bloc { border-top: 1px dashed #e7d9a8; margin-top: 6px; }
.apercu-zone { position: relative; background: #2b2b2b; display: flex; align-items: center; justify-content: center; height: 72vh; overflow: auto; }
.apercu-iframe { width: 100%; height: 100%; border: none; background: #fff; }
.apercu-img { max-width: 100%; max-height: 100%; object-fit: contain; }
.nav-btn { position: absolute; top: 50%; transform: translateY(-50%); z-index: 2; opacity: 0.92; }
.nav-gauche { left: 12px; }
.nav-droite { right: 12px; }
</style>
