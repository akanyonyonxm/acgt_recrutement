<script setup>
import { ref, computed } from 'vue'
import api from '../../api'
import { useAuthStore } from '../../stores/auth'
import StatCard from '../../components/StatCard.vue'

const auth = useAuthStore()
const STORAGE_FILTRES = `acgt_filtres_recours_${auth.utilisateur?.id ?? 'anon'}`
const sauve = JSON.parse(localStorage.getItem(STORAGE_FILTRES) || '{}')

const recours = ref([])
const total = ref(0)
const chargement = ref(false)
const stats = ref({ total: 0, en_attente: 0, valide: 0, rejete: 0 })

const statut = ref(sauve.statut ?? '')
const q = ref(sauve.q ?? '')
const tri = ref(Array.isArray(sauve.tri) ? sauve.tri : [])

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
  { title: 'Statut', key: 'statut' },
  { title: 'Reçu le', key: 'cree_le' },
  { title: '', key: 'actions', sortable: false, align: 'end' },
]
const TRI = { nom: 'nom', statut: 'statut', cree_le: 'cree_le' }

const cle = computed(() => `${statut.value}|${q.value}`)

function memoriser() {
  localStorage.setItem(STORAGE_FILTRES, JSON.stringify({
    statut: statut.value, q: q.value, tri: tri.value,
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

// --- Aperçu de document (in-app) ---
const apercu = ref({ show: false, url: '', titre: '' })
function voirDocument(doc) {
  apercu.value = { show: true, url: doc.url + '?inline=1', titre: doc.libelle || doc.nom_original }
}

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
</script>

<template>
  <div>
    <div class="d-flex align-center flex-wrap ga-3 mb-5">
      <v-icon color="primary" size="32">mdi-gavel</v-icon>
      <h1 class="text-h5 font-weight-bold text-primary mb-0">Recours</h1>
      <v-spacer />
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
            <v-btn v-if="auth.peutTraiter && detail.statut !== 'en_attente'" variant="text"
                   prepend-icon="mdi-lock-open-variant-outline" :loading="enAction" @click="rouvrir">
              Rouvrir
            </v-btn>
            <v-spacer />
            <v-btn variant="text" @click="dialog = false">Fermer</v-btn>
            <template v-if="auth.peutTraiter && detail.statut !== 'rejete'">
              <v-btn color="error" variant="tonal" prepend-icon="mdi-close-circle-outline"
                     :loading="enAction" @click="demanderDecision('rejeter')">Rejeter</v-btn>
            </template>
            <template v-if="auth.peutTraiter && detail.statut !== 'valide'">
              <v-btn color="success" variant="flat" prepend-icon="mdi-check-decagram-outline"
                     :loading="enAction" @click="demanderDecision('valider')">Valider</v-btn>
            </template>
          </template>
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

    <!-- Aperçu de document -->
    <v-dialog v-model="apercu.show" max-width="980" scrollable>
      <v-card rounded="lg">
        <v-card-title class="d-flex align-center ga-2 pa-3">
          <v-icon color="primary">mdi-file-eye-outline</v-icon>
          <span class="text-subtitle-1">{{ apercu.titre }}</span>
          <v-spacer />
          <v-btn variant="text" size="small" :href="apercu.url" target="_blank"
                 prepend-icon="mdi-open-in-new">Onglet</v-btn>
          <v-btn icon="mdi-close" variant="text" size="small" @click="apercu.show = false" />
        </v-card-title>
        <v-divider />
        <v-card-text class="pa-0" style="height: 72vh">
          <iframe v-if="apercu.url" :src="apercu.url" title="Aperçu" class="apercu-frame" />
        </v-card-text>
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
.apercu-frame { width: 100%; height: 100%; border: 0; }
.confirm-tete { display: flex; align-items: center; gap: 10px; padding: 16px 20px; }
.confirm-valider { border-top: 4px solid #2E7D32; }
.confirm-valider .confirm-tete { background: #E8F5E9; color: #1B5E20; }
.confirm-rejeter { border-top: 4px solid #C62828; }
.confirm-rejeter .confirm-tete { background: #FDECEA; color: #8B2C26; }
</style>
