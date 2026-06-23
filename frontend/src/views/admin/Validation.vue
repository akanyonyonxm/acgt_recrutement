<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api'
import StatutBadge from '../../components/StatutBadge.vue'
import StatCard from '../../components/StatCard.vue'
import { useAuthStore } from '../../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const dossiers = ref([])
const appels = ref([])
const agents = ref([])           // agents pouvant traiter (admin/validateur)
const monId = computed(() => auth.utilisateur?.id)
// Décision sur un dossier précis : un admin peut toujours ; un validateur
// seulement si le dossier LUI est affecté (cohérent avec le contrôle serveur).
function peutDecider(d) {
  if (auth.peutSuperviser) return true     // admin ou superviseur : toujours
  return auth.estValidateur && d?.affecte_a === monId.value
}

// Répartition de la charge (admin)
const dialogRepartir = ref(false)
const agentsChoisis = ref([])
const enRepartition = ref(false)
const resultatRepartition = ref(null)
const reequilibrer = ref(false)   // réaffecter aussi les déjà affectés
// Catégorie déjà décidée (retenus / non-retenus / rejetés) : révision réservée
// aux superviseurs. File « à valider » (déposé/examen) : agents de traitement.
const categorieDecidee = computed(() =>
  statut.value.split(',').some((s) => ['retenu', 'non_retenu', 'rejete'].includes(s)))
const agentsEligibles = computed(() => agents.value.filter((a) =>
  categorieDecidee.value
    ? (a.roles.includes('admin') || a.roles.includes('superviseur'))
    : true))

// Filtres mémorisés (localStorage) : on les retrouve au retour sur la page,
// notamment après avoir ouvert un dossier pour le traiter — pas besoin de
// refiltrer à chaque fois. Survit aussi à un rechargement.
// Clé SUFFIXÉE par l'id de l'utilisateur connecté : les filtres sont propres à
// chaque compte et ne fuient pas d'une session à l'autre sur la même machine.
const STORAGE_FILTRES = `acgt_filtres_validation_${auth.utilisateur?.id ?? 'anon'}`
function filtresSauvegardes() {
  try { return JSON.parse(localStorage.getItem(STORAGE_FILTRES)) || {} } catch { return {} }
}
const sauve = filtresSauvegardes()

const statut = ref(sauve.statut ?? 'depose,en_examen')
const appel = ref(sauve.appel ?? null)
const eligibilite = ref(sauve.eligibilite ?? null)
const doublons = ref(sauve.doublons ?? false)
const q = ref(sauve.q ?? '')
// Filtre d'affectation. Un validateur (non admin) voit son lot par défaut ;
// un admin voit tout. '' = tous, 'moi', 'aucune', '<id>' (admin).
const affecteParDefaut = (auth.estValidateur && !auth.estAdmin) ? 'moi' : ''
const affecte = ref(sauve.affecte ?? affecteParDefaut)
// Origine : '' (toutes), 'reclamation', 'en_ligne'.
const origine = ref(sauve.origine ?? '')
// Tri mémorisé (par utilisateur) : tableau Vuetify [{ key, order }].
const tri = ref(Array.isArray(sauve.tri) ? sauve.tri : [])

watch([statut, appel, eligibilite, doublons, q, affecte, origine, tri], () => {
  localStorage.setItem(STORAGE_FILTRES, JSON.stringify({
    statut: statut.value, appel: appel.value, eligibilite: eligibilite.value,
    doublons: doublons.value, q: q.value, affecte: affecte.value,
    origine: origine.value, tri: tri.value,
  }))
}, { deep: true })

// Options du filtre « affecté à ».
const optionsAffecte = computed(() => {
  if (!auth.estAdmin) {
    return [{ value: 'moi', title: 'Les miens' }, { value: '', title: 'Tous' }]
  }
  return [
    { value: '', title: 'Tous les agents' },
    { value: 'moi', title: 'Les miens' },
    { value: 'aucune', title: 'Non affectés' },
    ...agents.value.map((a) => ({ value: String(a.id), title: a.nom })),
  ]
})

// Options du filtre « Éligibilité » (alignées sur les badges de la colonne).
const ELIGIBILITE_OPTIONS = [
  { value: 'rattache', title: 'Rattaché' },
  { value: 'a_rattacher', title: 'À rattacher (nom complet trouvé)' },
  { value: 'partielle', title: 'Correspondance partielle' },
  { value: 'aucune', title: 'Aucune correspondance' },
]
const chargement = ref(false)
const total = ref(0)
const stats = ref({ total: 0, par_statut: {} })
const snack = ref({ show: false, color: 'success', text: '' })
const notifier = (text, color = 'success') => (snack.value = { show: true, color, text })

// « À valider » regroupe DÉPOSÉ et EN_EXAMEN (l'étape examen n'est plus
// utilisée : les dossiers qui y restent sont traités comme « à valider »).
// Dossiers REÇUS RÉELS = hors brouillon ET hors résidus annulés (dossiers de
// validation orphelins). Clé sentinelle 'recus' (pas une liste de statuts) :
// gérée à part dans charger() (statut hors brouillon + hors_residus=1). Les
// brouillons et les résidus restent visibles via leurs propres filtres/histo.
const STATUTS_RECUS = 'depose,en_examen,retenu,non_retenu,rejete'
const KPIS = [
  { key: 'recus', label: 'Reçus', desc: 'Hors brouillon & résidus', icon: 'mdi-folder-multiple', color: '#1a237e' },
  { key: 'depose,en_examen', label: 'À valider', desc: 'En attente', icon: 'mdi-inbox-arrow-down', color: '#EF6C00' },
  { key: 'retenu', label: 'Retenus', desc: 'Candidats retenus', icon: 'mdi-check-circle', color: '#2E7D32' },
  { key: 'rejete', label: 'Rejetés', desc: 'Refusés', icon: 'mdi-cancel', color: '#607D8B' },
]
// Clé 'recus' → comptes « réels » du back ; clé composite (« depose,en_examen »)
// → somme des statuts ; '' → total brut.
const compte = (key) => {
  if (key === 'recus') return stats.value.recus_reels || 0
  if (key === '') return stats.value.total
  return key.split(',').reduce((n, k) => n + (stats.value.par_statut[k] || 0), 0)
}

// Retenus (validés) par origine : issus d'une réclamation vs déposés en ligne.
const ORIGINES = [
  { key: 'reclamation', label: 'Réclamations validées', desc: 'Retenus issus d\'une réclamation', icon: 'mdi-account-alert-outline', color: '#6A1B9A' },
  { key: 'en_ligne', label: 'Éligibles validées', desc: 'Retenus déposés en ligne', icon: 'mdi-web', color: '#00838F' },
]
const compteOrigine = (k) => stats.value.par_origine?.[k] || 0
// Carte « validées » : clic = retenus de cette origine (statut retenu + origine).
const origineActive = (k) => origine.value === k && statut.value === 'retenu'
function filtrerOrigine(k) {
  if (origineActive(k)) { origine.value = ''; statut.value = 'depose,en_examen' }
  else { origine.value = k; statut.value = 'retenu' }
}

const ENTETES = [
  { title: 'Code', key: 'code', width: 110 },
  { title: 'Candidat', key: 'candidat', sortable: true },
  { title: 'Éligibilité', key: 'correspondance', sortable: false },
  { title: 'Nom sur la liste', key: 'eligibilite_nom', sortable: false },
  { title: 'Poste', key: 'poste_libelle' },
  { title: 'Affecté à', key: 'affecte_a_nom', sortable: false },
  { title: 'Statut', key: 'statut' },
  { title: 'Déposé le', key: 'cree_le' },
  { title: '', key: 'actions', sortable: false, align: 'end' },
]

// Libellés des champs qui coïncident avec la liste d'éligibilité (badge
// indicatif, jamais bloquant) : on affiche précisément ce qui correspond.
const LIBELLE_CHAMP = { code: 'Code', nom: 'Nom', postnom: 'Postnom', prenom: 'Prénom' }

// Mappe la clé de colonne triée -> champ de tri côté API (allowlist backend).
const TRI = {
  code: 'code', candidat: 'nom', poste_libelle: 'poste__libelle',
  appel_titre: 'appel__titre', statut: 'statut', cree_le: 'cree_le',
}

// Clé réactive : tout changement de filtre/recherche recharge le tableau (page 1).
const cle = computed(() => `${statut.value}|${appel.value || ''}|${eligibilite.value || ''}|${doublons.value}|${affecte.value}|${origine.value}|${q.value}`)

async function charger({ page = 1, itemsPerPage = 25, sortBy } = {}) {
  chargement.value = true
  try {
    // Le tableau pilote le tri : on mémorise son choix (persistance par user).
    if (sortBy !== undefined) tri.value = sortBy
    const s = tri.value && tri.value[0]
    const params = { page, page_size: itemsPerPage > 0 ? itemsPerPage : 25 }
    if (statut.value === 'recus') {
      // Vue « reçus réels » : hors brouillon + hors résidus annulés.
      params.statut = STATUTS_RECUS
      params.hors_residus = 1
    } else if (statut.value) {
      params.statut = statut.value
    }
    if (appel.value) params.appel = appel.value
    if (eligibilite.value) params.correspondance = eligibilite.value
    if (doublons.value) params.doublons = 1
    if (affecte.value) params.affecte = affecte.value
    // L'origine (réclamation / en ligne) ne filtre que les retenus.
    if (origine.value && statut.value === 'retenu') params.origine = origine.value
    if (q.value) params.q = q.value
    if (s && TRI[s.key]) {
      params.ordering = (s.order === 'desc' ? '-' : '') + TRI[s.key]
    }
    const { data } = await api.get('/dossiers/', { params })
    dossiers.value = data.results
    total.value = data.count
  } finally {
    chargement.value = false
  }
}

async function chargerStats() {
  const params = {}
  if (appel.value) params.appel = appel.value
  const { data } = await api.get('/dossiers/stats/', { params })
  stats.value = data
}

// Histogramme : brouillons + déposés ventilés par correspondance.
const histo = ref(null)
// Accordéon : repliable pour gagner de l'espace pendant le traitement. État
// mémorisé (ouvert par défaut au premier passage).
const STORAGE_HISTO = `acgt_histo_ouvert_${auth.utilisateur?.id ?? 'anon'}`
const histoOuvert = ref(localStorage.getItem(STORAGE_HISTO) !== '0')
watch(histoOuvert, (v) => localStorage.setItem(STORAGE_HISTO, v ? '1' : '0'))
async function chargerHisto() {
  const params = {}
  if (appel.value) params.appel = appel.value
  const { data } = await api.get('/dossiers/stats-correspondance/', { params })
  histo.value = data
}
// Barres de l'histogramme (clic → applique le filtre statut + éligibilité).
const BARRES = [
  { cle: 'brouillon', label: 'Brouillon', desc: 'Non soumis', couleur: '#90A4AE', statut: 'brouillon', elig: null },
  { cle: 'rattache', label: 'Rattaché', desc: 'Déposé', couleur: '#2E7D32', statut: 'depose', elig: 'rattache' },
  { cle: 'a_rattacher', label: 'À rattacher', desc: 'Déposé', couleur: '#43A047', statut: 'depose', elig: 'a_rattacher' },
  { cle: 'partielle', label: 'Partielle', desc: 'Déposé', couleur: '#0288D1', statut: 'depose', elig: 'partielle' },
  { cle: 'aucune', label: 'Aucune', desc: 'Déposé', couleur: '#C62828', statut: 'depose', elig: 'aucune' },
]
function valeurBarre(cle) {
  if (!histo.value) return 0
  return cle === 'brouillon' ? histo.value.brouillon : (histo.value.depose?.[cle] || 0)
}
const histoMax = computed(() => Math.max(1, ...BARRES.map((b) => valeurBarre(b.cle))))
const histoTotal = computed(() =>
  histo.value ? histo.value.brouillon + (histo.value.depose?.total || 0) : 0)
function filtrerBarre(b) {
  statut.value = b.statut
  eligibilite.value = b.elig
  doublons.value = false
  origine.value = ''   // l'origine ne s'applique qu'aux retenus
}

// Clic sur une carte de statut : on réinitialise l'origine (sous-filtre des
// « validées par origine », réservé aux retenus) pour ne pas la cumuler.
function filtrer(key) { statut.value = key; origine.value = '' }
function changerAppel() { chargerStats(); chargerHisto() }   // le tableau se recharge via cle

// Répartit le sous-ensemble FILTRÉ (statut + éligibilité + appel + doublons +
// recherche), non encore affecté, entre les agents choisis (round-robin serveur).
async function repartir() {
  if (!agentsChoisis.value.length) {
    notifier('Sélectionnez au moins un agent.', 'error'); return
  }
  enRepartition.value = true
  resultatRepartition.value = null
  try {
    const corps = { agents: agentsChoisis.value, seulement_non_affectes: !reequilibrer.value }
    if (statut.value) corps.statut = statut.value
    if (appel.value) corps.appel = appel.value
    if (eligibilite.value) corps.correspondance = eligibilite.value
    if (doublons.value) corps.doublons = 1
    if (q.value) corps.q = q.value
    const { data } = await api.post('/dossiers/repartir/', corps)
    resultatRepartition.value = data
    notifier(`${data.total_reparti} dossier(s) répartis entre ${data.par_agent.length} agent(s).`)
    await Promise.all([charger(), chargerStats()])
  } catch (e) {
    notifier(e.response?.data?.agents || e.response?.data?.detail || 'Répartition impossible.', 'error')
  } finally {
    enRepartition.value = false
  }
}

let minuteur
function rechercher() {
  clearTimeout(minuteur)
  minuteur = setTimeout(() => { q.value = q.value.trim() }, 300)
}

function ouvrir(_, { item }) { router.push({ name: 'dossier', params: { id: item.id } }) }
const dateFr = (d) => new Date(d).toLocaleDateString('fr-FR')

onMounted(async () => {
  const { data } = await api.get('/appels/')
  appels.value = data.results.map((a) => ({ value: a.id, title: a.titre }))
  // Agents pouvant traiter (pour répartir / filtrer) — admin et superviseur.
  if (auth.peutSuperviser) {
    try {
      const { data: us } = await api.get('/auth/utilisateurs/')
      agents.value = us
        .filter((u) => u.roles.includes('admin') || u.roles.includes('superviseur')
          || u.roles.includes('validateur'))
        .map((u) => ({ id: u.id, nom: `${u.prenom} ${u.nom}`.trim() || u.email, roles: u.roles }))
    } catch { /* non bloquant */ }
  }
  chargerStats()
  chargerHisto()
})
</script>

<template>
  <div>
    <!-- En-tête -->
    <div class="d-flex align-center flex-wrap ga-3 mb-5">
      <v-icon color="primary" size="30" class="mr-1">mdi-check-decagram-outline</v-icon>
      <h1 class="text-h5 font-weight-bold text-primary">Validation des dossiers</h1>
      <v-spacer />
      <v-text-field v-model="q" @update:modelValue="rechercher"
                    placeholder="Rechercher un candidat…" prepend-inner-icon="mdi-magnify"
                    variant="outlined" density="compact" hide-details clearable
                    style="max-width: 280px" @click:clear="q = ''" />
      <v-select v-model="eligibilite" :items="ELIGIBILITE_OPTIONS" label="Filtrer par éligibilité"
                clearable hide-details density="compact" variant="outlined" style="max-width: 240px"
                prepend-inner-icon="mdi-account-search-outline" />
      <v-select v-model="appel" :items="appels" label="Filtrer par appel" clearable hide-details
                density="compact" variant="outlined" style="max-width: 240px"
                @update:modelValue="changerAppel" />
      <v-select v-model="affecte" :items="optionsAffecte" label="Affecté à" hide-details
                density="compact" variant="outlined" style="max-width: 190px"
                prepend-inner-icon="mdi-account-arrow-right-outline" />
      <v-btn :variant="doublons ? 'flat' : 'outlined'" :color="doublons ? 'warning' : 'grey'"
             prepend-icon="mdi-content-duplicate" @click="doublons = !doublons">
        Doublons
      </v-btn>
      <v-btn v-if="auth.estAdmin" color="primary" variant="flat"
             prepend-icon="mdi-account-multiple-check-outline" @click="dialogRepartir = true">
        Répartir
      </v-btn>
    </div>

    <!-- KPI : statut (filtre) puis origine (réclamation / en ligne), même rangée -->
    <v-row dense class="mb-5">
      <v-col v-for="k in KPIS" :key="k.key" cols="6" sm="4" md="2">
        <StatCard :icon="k.icon" :value="compte(k.key)" :label="k.label" :description="k.desc"
                  :color="k.color" clickable :active="statut === k.key" @click="filtrer(k.key)" />
      </v-col>
      <v-col v-for="o in ORIGINES" :key="o.key" cols="6" sm="4" md="2">
        <StatCard :icon="o.icon" :value="compteOrigine(o.key)" :label="o.label" :description="o.desc"
                  :color="o.color" clickable :active="origineActive(o.key)" @click="filtrerOrigine(o.key)" />
      </v-col>
    </v-row>

    <!-- Histogramme (accordéon) : brouillons + déposés par correspondance -->
    <v-card v-if="histo" flat border class="histo-carte mb-5">
      <button class="histo-entete histo-toggle" @click="histoOuvert = !histoOuvert"
              :aria-expanded="histoOuvert">
        <div class="d-flex align-center" style="min-width:0">
          <v-icon class="histo-chevron" :class="{ ouvert: histoOuvert }" size="22">mdi-chevron-right</v-icon>
          <div style="min-width:0">
            <div class="histo-titre">Répartition des dossiers</div>
            <div class="histo-sous">
              Brouillons et dossiers déposés selon leur correspondance avec la liste d'éligibilité
            </div>
          </div>
        </div>
        <div class="histo-total">
          <span class="histo-total-val">{{ histoTotal }}</span>
          <span class="histo-total-lib">dossiers</span>
        </div>
      </button>
      <v-expand-transition>
        <div v-show="histoOuvert" class="histo-zone mt-4">
        <button v-for="b in BARRES" :key="b.cle" class="histo-ligne"
                :class="{ actif: statut === b.statut && eligibilite === b.elig }"
                @click="filtrerBarre(b)"
                :title="`Filtrer : ${b.label}`">
          <span class="histo-lbl">
            <span class="histo-pastille" :style="{ background: b.couleur }" />
            {{ b.label }}<span class="histo-desc">{{ b.desc }}</span>
          </span>
          <span class="histo-piste">
            <span class="histo-fill" :style="{
              width: (valeurBarre(b.cle) / histoMax * 100) + '%', background: b.couleur }" />
          </span>
          <span class="histo-val">{{ valeurBarre(b.cle) }}</span>
        </button>
        </div>
      </v-expand-transition>
    </v-card>

    <!-- Tableau -->
    <v-card flat border>
      <v-data-table-server
        :headers="ENTETES"
        :items="dossiers"
        :items-length="total"
        :loading="chargement"
        :search="cle"
        :sort-by="tri"
        :items-per-page="25"
        :items-per-page-options="[{ value: 25, title: '25' }, { value: 50, title: '50' }, { value: 100, title: '100' }]"
        @update:options="charger"
        @click:row="ouvrir"
        hover
        no-data-text="Aucun dossier dans cette catégorie."
        loading-text="Chargement…"
        class="tableau-admin"
      >
        <template #item.code="{ item }">
          <span class="font-weight-bold text-primary">{{ item.code || ('#' + item.id) }}</span>
        </template>
        <template #item.candidat="{ item }">
          <span class="font-weight-bold">{{ item.nom }}</span> {{ item.postnom }} {{ item.prenom }}
          <v-chip v-if="item.a_doublon" color="warning" size="x-small" label variant="tonal"
                  prepend-icon="mdi-content-duplicate" class="ml-1">Doublon</v-chip>
        </template>
        <template #item.correspondance="{ item }">
          <!-- Déjà rattaché à une personne de la liste -->
          <v-chip v-if="item.correspondance.etat === 'rattache'" color="success" variant="flat"
                  size="small" label prepend-icon="mdi-link-variant">Rattaché</v-chip>
          <!-- Nom complet trouvé sur la liste : prêt à rattacher -->
          <v-chip v-else-if="item.correspondance.etat === 'a_rattacher'" color="success" variant="tonal"
                  size="small" label prepend-icon="mdi-account-check">À rattacher</v-chip>
          <!-- Champs qui coïncident (code / nom / postnom / prénom) -->
          <div v-else-if="item.correspondance.etat === 'champs'" class="d-flex flex-wrap ga-1">
            <v-chip v-for="c in item.correspondance.champs" :key="c"
                    :color="c === 'code' ? 'success' : 'blue-grey'" variant="tonal" size="x-small" label>
              {{ LIBELLE_CHAMP[c] }}
            </v-chip>
          </div>
          <!-- Rien ne correspond -->
          <v-chip v-else color="error" variant="tonal" size="small" label
                  prepend-icon="mdi-help-circle-outline">Aucune</v-chip>
        </template>
        <template #item.eligibilite_nom="{ item }">
          <template v-if="item.eligibilite_nom">
            <span :class="item.eligibilite_nom.rattache ? 'font-weight-medium' : 'nom-code'">
              {{ item.eligibilite_nom.nom }}
            </span>
            <div v-if="item.eligibilite_nom.partiel" class="nom-code-hint">
              ressemblance partielle (code {{ item.eligibilite_nom.code }})
            </div>
            <div v-else-if="!item.eligibilite_nom.rattache" class="nom-code-hint">
              nom identique — à rattacher
            </div>
          </template>
          <span v-else class="text-medium-emphasis">—</span>
        </template>
        <template #item.poste_libelle="{ item }">{{ item.poste_libelle || '—' }}</template>
        <template #item.affecte_a_nom="{ item }">
          <v-chip v-if="item.affecte_a_nom" size="small" variant="tonal"
                  :color="item.affecte_a === monId ? 'primary' : 'grey'"
                  prepend-icon="mdi-account-outline">{{ item.affecte_a_nom }}</v-chip>
          <span v-else class="text-medium-emphasis">—</span>
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
      </v-data-table-server>
    </v-card>

    <!-- Répartition de la charge entre agents (admin) -->
    <v-dialog v-model="dialogRepartir" max-width="580">
      <v-card flat border rounded="lg">
        <v-card-title class="d-flex align-center ga-2 py-4">
          <v-icon color="primary">mdi-account-multiple-check-outline</v-icon>
          <span class="font-weight-bold">Répartir les dossiers à traiter</span>
        </v-card-title>
        <v-divider />
        <v-card-text>
          <v-alert type="info" variant="tonal" density="compact" class="mb-3">
            Les dossiers <strong>du filtre actuel</strong> seront distribués
            <strong>équitablement</strong> entre les agents choisis.
            <template v-if="reequilibrer"> <strong>Rééquilibrage</strong> : les déjà affectés sont aussi redistribués.</template>
            <template v-else> Les déjà affectés ne sont pas touchés.</template>
            <div class="mt-2 text-caption">
              Filtre :
              <strong>{{ (KPIS.find((k) => k.key === statut) || {}).label || 'Tous statuts' }}</strong>
              <template v-if="eligibilite">
                · éligibilité « {{ (ELIGIBILITE_OPTIONS.find((o) => o.value === eligibilite) || {}).title }} »
              </template>
              <template v-if="appel"> · 1 appel</template>
              <template v-if="doublons"> · doublons</template>
              <template v-if="q"> · recherche « {{ q }} »</template>
            </div>
          </v-alert>
          <!-- Catégorie décidée : révision réservée aux superviseurs -->
          <v-alert v-if="categorieDecidee" type="warning" variant="tonal" density="compact" class="mb-3"
                   icon="mdi-shield-account-outline">
            Catégorie déjà décidée : seuls les <strong>superviseurs</strong> peuvent être affectés (révision).
          </v-alert>
          <v-switch v-model="reequilibrer" color="primary" density="compact" hide-details class="mb-1"
                    label="Rééquilibrer (réaffecter aussi les déjà affectés)" />
          <v-select v-model="agentsChoisis" :items="agentsEligibles" item-title="nom" item-value="id"
                    label="Agents" multiple chips closable-chips
                    prepend-inner-icon="mdi-account-group-outline"
                    :hint="categorieDecidee ? 'Superviseurs uniquement pour cette catégorie.' : 'Agents qui traiteront ces dossiers.'"
                    persistent-hint />

          <div v-if="resultatRepartition" class="mt-4">
            <v-divider class="mb-3" />
            <div class="font-weight-bold mb-2">
              {{ resultatRepartition.total_reparti }} dossier(s) répartis :
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

    <v-snackbar v-model="snack.show" :color="snack.color" timeout="3500">{{ snack.text }}</v-snackbar>
  </div>
</template>

<style scoped>
/* Histogramme correspondance */
.histo-carte { border-radius: 16px; padding: 20px 22px 16px; }
.histo-entete { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.histo-toggle { width: 100%; background: none; border: none; cursor: pointer; text-align: left; padding: 2px; }
.histo-toggle:hover .histo-titre { color: #283593; }
.histo-chevron { color: #1a237e; margin-right: 8px; transition: transform 0.25s ease; flex-shrink: 0; }
.histo-chevron.ouvert { transform: rotate(90deg); }
.histo-titre { font-size: 1.05rem; font-weight: 800; color: #1a237e; }
.histo-sous { font-size: 0.8rem; color: #8a92a4; margin-top: 2px; }
.histo-total { text-align: right; line-height: 1.05; flex-shrink: 0; }
.histo-total-val { display: block; font-size: 1.5rem; font-weight: 800; color: #1a237e; }
.histo-total-lib { font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.04em; color: #9098a8; }
.histo-zone { display: flex; flex-direction: column; gap: 6px; }
.histo-ligne { display: grid; grid-template-columns: 150px 1fr 48px; align-items: center; gap: 12px;
  background: none; border: none; cursor: pointer; padding: 5px 8px; border-radius: 10px;
  transition: background 0.15s; text-align: left; }
.histo-ligne:hover { background: #f4f6fb; }
.histo-ligne.actif { background: #eef1fb; box-shadow: inset 0 0 0 2px #1a237e22; }
.histo-lbl { display: flex; align-items: center; gap: 8px; font-size: 0.85rem; font-weight: 700; color: #2c3344; white-space: nowrap; }
.histo-pastille { width: 11px; height: 11px; border-radius: 3px; flex-shrink: 0; }
.histo-desc { font-size: 0.64rem; text-transform: uppercase; letter-spacing: 0.03em; color: #9098a8; font-weight: 600; }
.histo-piste { height: 18px; background: #f1f3f8; border-radius: 9px; overflow: hidden; }
.histo-fill { display: block; height: 100%; min-width: 3px; border-radius: 9px;
  transition: width 0.55s cubic-bezier(0.22, 1, 0.36, 1); }
.histo-val { font-size: 1rem; font-weight: 800; color: #1f2430; text-align: right; }
@media (max-width: 600px) {
  .histo-ligne { grid-template-columns: 120px 1fr 40px; gap: 8px; }
  .histo-lbl { font-size: 0.78rem; }
  .histo-desc { display: none; }
}

.tableau-admin :deep(thead th) { background: #f4f5f9; font-weight: 700 !important; color: #1a237e !important; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.03em; }
.tableau-admin :deep(tbody tr) { cursor: pointer; }
/* Nom de la liste affiché pour un dossier NON rattaché (juste le propriétaire du code) */
.nom-code { color: #8a94a6; font-style: italic; }
.nom-code-hint { font-size: 0.68rem; color: #b0b7c3; }
</style>
