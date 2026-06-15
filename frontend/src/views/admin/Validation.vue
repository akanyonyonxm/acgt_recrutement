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

const statut = ref(sauve.statut ?? 'depose')
const appel = ref(sauve.appel ?? null)
const eligibilite = ref(sauve.eligibilite ?? null)
const doublons = ref(sauve.doublons ?? false)
const q = ref(sauve.q ?? '')

watch([statut, appel, eligibilite, doublons, q], () => {
  localStorage.setItem(STORAGE_FILTRES, JSON.stringify({
    statut: statut.value, appel: appel.value, eligibilite: eligibilite.value,
    doublons: doublons.value, q: q.value,
  }))
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

const KPIS = [
  { key: '', label: 'Total', desc: 'Tous les dossiers', icon: 'mdi-folder-multiple', color: '#1a237e' },
  { key: 'depose', label: 'À valider', desc: 'En attente', icon: 'mdi-inbox-arrow-down', color: '#EF6C00' },
  { key: 'en_examen', label: 'En examen', desc: 'En cours', icon: 'mdi-magnify-scan', color: '#0288D1' },
  { key: 'retenu', label: 'Retenus', desc: 'Candidats retenus', icon: 'mdi-check-circle', color: '#2E7D32' },
  { key: 'non_retenu', label: 'Non retenus', desc: 'Écartés', icon: 'mdi-close-circle', color: '#C62828' },
  { key: 'rejete', label: 'Rejetés', desc: 'Refusés', icon: 'mdi-cancel', color: '#607D8B' },
]
const compte = (key) => (key === '' ? stats.value.total : stats.value.par_statut[key] || 0)

const ENTETES = [
  { title: 'Code', key: 'code', width: 110 },
  { title: 'Candidat', key: 'candidat', sortable: true },
  { title: 'Éligibilité', key: 'correspondance', sortable: false },
  { title: 'Nom sur la liste', key: 'eligibilite_nom', sortable: false },
  { title: 'Poste', key: 'poste_libelle' },
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
const cle = computed(() => `${statut.value}|${appel.value || ''}|${eligibilite.value || ''}|${doublons.value}|${q.value}`)

async function charger({ page = 1, itemsPerPage = 25, sortBy = [] } = {}) {
  chargement.value = true
  try {
    const params = { page, page_size: itemsPerPage > 0 ? itemsPerPage : 25 }
    if (statut.value) params.statut = statut.value
    if (appel.value) params.appel = appel.value
    if (eligibilite.value) params.correspondance = eligibilite.value
    if (doublons.value) params.doublons = 1
    if (q.value) params.q = q.value
    if (sortBy.length && TRI[sortBy[0].key]) {
      params.ordering = (sortBy[0].order === 'desc' ? '-' : '') + TRI[sortBy[0].key]
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
}

function filtrer(key) { statut.value = key }     // -> cle change -> tableau rechargé
function changerAppel() { chargerStats(); chargerHisto() }   // le tableau se recharge via cle

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
      <v-btn :variant="doublons ? 'flat' : 'outlined'" :color="doublons ? 'warning' : 'grey'"
             prepend-icon="mdi-content-duplicate" @click="doublons = !doublons">
        Doublons
      </v-btn>
    </div>

    <!-- KPI -->
    <v-row dense class="mb-5">
      <v-col v-for="k in KPIS" :key="k.key" cols="6" sm="4" md="2">
        <StatCard :icon="k.icon" :value="compte(k.key)" :label="k.label" :description="k.desc"
                  :color="k.color" clickable :active="statut === k.key" @click="filtrer(k.key)" />
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
