<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../../api'
import { useAuthStore } from '../../stores/auth'
import { useCandidatureStore } from '../../stores/candidature'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const cand = useCandidatureStore()

const etape = ref(1)
const appels = ref([])
const postes = ref([])
const mesAppels = ref(new Set())   // appels où le candidat a déjà un dossier
const appelSelectionne = ref(null)
const form = ref({ appel: null, poste: null, nom: '', postnom: '', prenom: '', email: '' })
const dossier = ref(null)
const erreur = ref('')
const snack = ref({ show: false, color: 'success', text: '' })
const enCours = ref(false)
const enUpload = ref({})       // type_piece.id -> bool
const soumis = ref(false)

const complet = computed(() => dossier.value && dossier.value.pieces_manquantes?.length === 0)
const piecesExigees = computed(() => appelSelectionne.value?.pieces_exigees || [])
const notifier = (text, color = 'success') => (snack.value = { show: true, color, text })

const fichiersDuType = (typeId) => (dossier.value?.pieces || []).filter((p) => p.type_piece.id === typeId)

const ICONE_PIECE = { cv: 'mdi-file-account', identite: 'mdi-card-account-details', diplome: 'mdi-school', attestation_stage: 'mdi-certificate' }
const iconePiece = (code) => ICONE_PIECE[code] || 'mdi-file-document'
const dateCourte = (d) => new Date(d).toLocaleDateString('fr-FR')
const kos = (o) => (o > 1024 * 1024 ? (o / 1048576).toFixed(1) + ' Mo' : Math.round(o / 1024) + ' Ko')

// Un appel est bloqué si « candidature unique » et déjà postulé par ce compte.
const appelBloque = (a) => a?.candidature_unique && mesAppels.value.has(a.id)
const appelItems = computed(() => appels.value.map((a) => ({
  value: a.id,
  title: a.titre + (appelBloque(a) ? ' — déjà postulé' : ''),
  disabled: appelBloque(a),
})))

onMounted(async () => {
  const [{ data }, { data: dp }, { data: dd }] = await Promise.all([
    api.get('/appels/'),
    api.get('/postes/'),
    api.get('/dossiers/'),
  ])
  appels.value = data.results.filter((a) => a.statut === 'publie')
  postes.value = dp.results.map((p) => ({ value: p.id, title: p.libelle }))
  mesAppels.value = new Set(dd.results.map((d) => d.appel))
  if (route.query.dossier) {
    const { data: d } = await api.get(`/dossiers/${route.query.dossier}/`)
    dossier.value = d
    appelSelectionne.value = (await api.get(`/appels/${d.appel}/`)).data
    // Pré-remplit le formulaire pour permettre le retour à l'étape 1.
    form.value = {
      appel: d.appel, poste: d.poste, nom: d.nom,
      postnom: d.postnom, prenom: d.prenom, email: d.email,
    }
    etape.value = 2
  } else {
    form.value.email = auth.utilisateur?.email || ''
  }
})

function choisirAppel(id) {
  form.value.appel = id
  appelSelectionne.value = appels.value.find((a) => a.id === id) || null
}

async function creerDossier() {
  erreur.value = ''
  enCours.value = true
  try {
    // Si le brouillon existe déjà (retour en arrière), on le met à jour
    // au lieu d'en créer un nouveau.
    const { data } = dossier.value
      ? await api.patch(`/dossiers/${dossier.value.id}/`, form.value)
      : await api.post('/dossiers/', form.value)
    dossier.value = data
    etape.value = 2
  } catch (e) {
    erreur.value = e.response?.data?.appel?.[0] || e.response?.data?.detail || 'Enregistrement impossible.'
  } finally {
    enCours.value = false
  }
}

async function rafraichir() {
  dossier.value = (await api.get(`/dossiers/${dossier.value.id}/`)).data
}

// Ouvre le sélecteur de fichier puis téléverse automatiquement.
function declencher(typeId) {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.pdf,.jpg,.jpeg,.png,.doc,.docx'
  input.onchange = (e) => {
    const f = e.target.files?.[0]
    if (f) onFichier(typeId, f)
  }
  input.click()
}

async function onFichier(typeId, f) {
  enUpload.value[typeId] = true
  const fd = new FormData()
  fd.append('type_piece', typeId)
  fd.append('fichier', f)
  try {
    await api.post(`/dossiers/${dossier.value.id}/pieces/`, fd)
    await rafraichir()
    notifier('Pièce ajoutée.')
  } catch (e) {
    notifier(e.response?.data?.fichier?.[0] || e.response?.data?.detail || 'Téléversement impossible.', 'error')
  } finally {
    enUpload.value[typeId] = false
  }
}

async function retirerPiece(pieceId) {
  await api.delete(`/dossiers/${dossier.value.id}/pieces/${pieceId}/`)
  await rafraichir()
}

async function soumettre() {
  enCours.value = true
  try {
    await api.post(`/dossiers/${dossier.value.id}/soumettre/`)
    soumis.value = true
    etape.value = 3
    cand.rafraichir()   // met à jour la disponibilité du bouton « Postuler »
  } catch (e) {
    notifier(e.response?.data?.detail || 'Soumission impossible.', 'error')
  } finally {
    enCours.value = false
  }
}
</script>

<template>
  <v-container class="py-8 px-6" style="max-width: 880px">
    <div class="mb-6">
      <h1 class="text-h4 font-weight-bold text-primary">Déposer un dossier</h1>
      <p class="text-body-1 text-medium-emphasis mb-0">
        Trois étapes : vos informations, vos pièces justificatives, puis la confirmation.
      </p>
    </div>

    <v-card flat border class="mb-6 px-2 py-1">
      <v-stepper v-model="etape" alt-labels flat class="bg-transparent" :elevation="0">
        <v-stepper-header style="box-shadow:none">
          <v-stepper-item :value="1" title="Informations" :complete="etape > 1" color="primary" />
          <v-divider />
          <v-stepper-item :value="2" title="Pièces" :complete="etape > 2" color="primary" />
          <v-divider />
          <v-stepper-item :value="3" title="Confirmation" color="primary" />
        </v-stepper-header>
      </v-stepper>
    </v-card>

    <!-- ÉTAPE 1 -->
    <v-card v-if="etape === 1" flat border class="pa-2">
      <v-card-text>
        <v-select :model-value="form.appel" @update:modelValue="choisirAppel"
                  :items="appelItems" :item-props="(i) => ({ disabled: i.disabled })"
                  label="Appel à candidature" prepend-inner-icon="mdi-bullhorn" class="mb-2" />
        <v-alert v-if="appelSelectionne && appelBloque(appelSelectionne)" type="warning"
                 variant="tonal" density="compact" class="mb-2">
          Vous avez déjà postulé à cet appel : une seule candidature est autorisée.
        </v-alert>
        <v-select v-model="form.poste" :items="postes"
                  label="Poste / fonction visé(e)" prepend-inner-icon="mdi-briefcase" class="mb-2" />
        <v-expand-transition>
          <v-alert v-if="appelSelectionne" type="info" variant="tonal" density="compact" class="mb-4">
            Pièces à fournir :
            {{ piecesExigees.map((p) => p.type_piece.libelle + (p.obligatoire ? '' : ' (facultatif)')).join(', ') }}
          </v-alert>
        </v-expand-transition>
        <v-row dense>
          <v-col cols="12" sm="4"><v-text-field v-model="form.nom" label="Nom" /></v-col>
          <v-col cols="12" sm="4"><v-text-field v-model="form.postnom" label="Post-nom" /></v-col>
          <v-col cols="12" sm="4"><v-text-field v-model="form.prenom" label="Prénom" /></v-col>
        </v-row>
        <v-text-field v-model="form.email" label="Email de contact" type="email" prepend-inner-icon="mdi-email"
                      hint="Vous (ou un proche) y recevrez le suivi du dossier" persistent-hint />
        <v-alert v-if="erreur" type="error" variant="tonal" density="compact" class="mt-3">{{ erreur }}</v-alert>
      </v-card-text>
      <v-card-actions class="px-4 pb-4">
        <v-btn variant="text" :to="{ name: 'mes-dossiers' }">Annuler</v-btn>
        <v-spacer />
        <v-btn color="accent" variant="flat" size="large" rounded="lg" class="text-primary font-weight-bold"
               append-icon="mdi-arrow-right" :loading="enCours"
               :disabled="!form.appel || !form.poste || !form.nom || !form.prenom || !form.email || appelBloque(appelSelectionne)"
               @click="creerDossier">
          Continuer
        </v-btn>
      </v-card-actions>
    </v-card>

    <!-- ÉTAPE 2 : pièces justificatives -->
    <div v-else-if="etape === 2">
      <div class="d-flex align-center flex-wrap mb-4">
        <span class="text-h6 font-weight-bold text-primary">Pièces justificatives</span>
        <v-spacer />
        <span class="text-caption text-medium-emphasis font-italic">Formats acceptés : PDF, JPG, PNG, Word · 5 Mo max</span>
      </div>

      <v-row>
        <v-col v-for="pe in piecesExigees" :key="pe.id" cols="12" md="6">
          <v-card class="piece-carte h-100 pa-5" :class="{ deposee: fichiersDuType(pe.type_piece.id).length }">
            <div class="d-flex justify-space-between align-start mb-3">
              <v-avatar color="primary" variant="tonal" rounded="lg" size="46">
                <v-icon>{{ iconePiece(pe.type_piece.code) }}</v-icon>
              </v-avatar>
              <v-chip :color="pe.obligatoire ? 'warning' : 'grey'" size="small" variant="tonal" label>
                {{ pe.obligatoire ? 'Obligatoire' : 'Facultatif' }}
              </v-chip>
            </div>
            <div class="text-subtitle-1 font-weight-bold">{{ pe.type_piece.libelle }}</div>
            <p class="text-caption text-medium-emphasis mb-3">
              {{ pe.type_piece.description
                 || (pe.type_piece.code === 'diplome' ? 'Joignez vos diplômes académiques les plus récents.' : 'Document requis pour votre dossier.') }}
            </p>

            <!-- fichiers déposés -->
            <div v-for="p in fichiersDuType(pe.type_piece.id)" :key="p.id" class="fichier-box mb-2">
              <v-icon color="success" class="mr-2">mdi-check-circle</v-icon>
              <div class="flex-grow-1" style="min-width:0">
                <div class="fichier-nom">{{ p.nom_original }}</div>
                <div class="fichier-meta">Déposé le {{ dateCourte(p.cree_le) }} · {{ kos(p.taille) }}</div>
              </div>
              <v-btn icon="mdi-delete-outline" variant="text" color="error" size="small" @click="retirerPiece(p.id)" />
            </div>

            <!-- zone de téléversement -->
            <button v-if="!fichiersDuType(pe.type_piece.id).length || pe.multiple"
                    class="upload-zone" :disabled="enUpload[pe.type_piece.id]"
                    @click="declencher(pe.type_piece.id)">
              <v-icon class="mr-2">{{ enUpload[pe.type_piece.id] ? 'mdi-loading mdi-spin' : 'mdi-upload' }}</v-icon>
              <template v-if="fichiersDuType(pe.type_piece.id).length">Ajouter un autre diplôme</template>
              <template v-else>{{ pe.type_piece.code === 'diplome' ? 'Télécharger un diplôme' : 'Télécharger le document' }}</template>
            </button>
          </v-card>
        </v-col>
      </v-row>

      <v-divider class="my-6" />
      <div class="d-flex align-center flex-wrap ga-3">
        <v-btn variant="outlined" color="primary" prepend-icon="mdi-arrow-left" @click="etape = 1">Précédent</v-btn>
        <v-spacer />
        <v-btn color="accent" variant="flat" size="large" rounded="lg" class="text-primary font-weight-bold"
               append-icon="mdi-arrow-right" :disabled="!complet" @click="etape = 3">Suivant</v-btn>
      </div>
    </div>

    <!-- ÉTAPE 3 -->
    <div v-else>
      <div v-if="!soumis">
        <v-card flat border class="pa-6 mb-4">
          <div class="text-subtitle-1 font-weight-bold text-primary mb-4">
            <v-icon color="primary" class="mr-2">mdi-clipboard-check-outline</v-icon>
            Vérifiez votre candidature
          </div>

          <v-row dense>
            <v-col cols="12" sm="6">
              <div class="recap-tuile">
                <v-icon color="primary" class="mr-3">mdi-bullhorn-outline</v-icon>
                <div><div class="recap-label">Appel à candidature</div>
                  <div class="recap-valeur">{{ appelSelectionne?.titre }}</div></div>
              </div>
            </v-col>
            <v-col cols="12" sm="6">
              <div class="recap-tuile">
                <v-icon color="primary" class="mr-3">mdi-briefcase-outline</v-icon>
                <div><div class="recap-label">Poste visé</div>
                  <div class="recap-valeur">{{ dossier.poste_libelle }}</div></div>
              </div>
            </v-col>
            <v-col cols="12" sm="6">
              <div class="recap-tuile">
                <v-icon color="primary" class="mr-3">mdi-account-outline</v-icon>
                <div><div class="recap-label">Candidat</div>
                  <div class="recap-valeur">
                    {{ form.nom || dossier.nom }} {{ form.postnom || dossier.postnom }} {{ form.prenom || dossier.prenom }}
                  </div></div>
              </div>
            </v-col>
            <v-col cols="12" sm="6">
              <div class="recap-tuile">
                <v-icon color="primary" class="mr-3">mdi-email-outline</v-icon>
                <div><div class="recap-label">Email de contact</div>
                  <div class="recap-valeur">{{ dossier.email }}</div></div>
              </div>
            </v-col>
          </v-row>

          <div class="recap-label mt-5 mb-2">Pièces jointes ({{ dossier.pieces.length }})</div>
          <div class="d-flex flex-column ga-2">
            <div v-for="p in dossier.pieces" :key="p.id" class="piece-ligne">
              <v-icon color="primary" size="20" class="mr-2">mdi-file-check</v-icon>
              <span class="font-weight-bold mr-1">{{ p.type_piece.libelle }}</span>
              <span class="text-medium-emphasis text-truncate">— {{ p.nom_original }}</span>
            </div>
          </div>

          <v-alert type="info" variant="tonal" density="compact" class="mt-5">
            Une fois soumis, le dossier ne pourra plus être modifié. Un accusé de réception vous sera envoyé par email.
          </v-alert>
        </v-card>

        <div class="d-flex align-center flex-wrap ga-3">
          <v-btn variant="text" prepend-icon="mdi-arrow-left" @click="etape = 2">Précédent</v-btn>
          <v-spacer />
          <v-btn color="success" variant="flat" size="large" prepend-icon="mdi-send" :loading="enCours" @click="soumettre">
            Soumettre le dossier
          </v-btn>
        </div>
      </div>

      <v-card v-else flat border class="pa-10 text-center">
        <v-icon color="success" size="72" class="mb-3">mdi-check-circle</v-icon>
        <h2 class="text-h5 text-primary mb-2">Dossier soumis !</h2>
        <p class="text-body-1 mb-1">Votre dossier <strong>#{{ dossier.id }}</strong> a bien été enregistré.</p>
        <p class="text-body-2 text-medium-emphasis mb-6">
          Un accusé de réception vous a été envoyé. Suivez son statut dans « Mes dossiers ».
        </p>
        <v-btn color="primary" variant="flat" :to="{ name: 'mes-dossiers' }" prepend-icon="mdi-folder-account">
          Voir mes dossiers
        </v-btn>
      </v-card>
    </div>

    <v-snackbar v-model="snack.show" :color="snack.color" timeout="3000">{{ snack.text }}</v-snackbar>
  </v-container>
</template>

<style scoped>
.piece-carte {
  border: 1px solid #e2e6ea;
  border-radius: 16px;
  transition: box-shadow 0.2s, border-color 0.2s;
}
.piece-carte:hover { box-shadow: 0 4px 16px rgba(26, 35, 126, 0.08); }
.piece-carte.deposee { border-color: #388E3C; }

.upload-zone {
  width: 100%; display: flex; align-items: center; justify-content: center;
  border: 1.5px dashed #b9c0cc; border-radius: 12px; padding: 13px;
  color: #1a237e; font-weight: 600; font-size: 0.9rem; background: transparent;
  cursor: pointer; transition: all 0.2s;
}
.upload-zone:hover:not(:disabled) { border-color: #1a237e; background: rgba(26,35,126,0.04); }
.upload-zone:disabled { opacity: 0.5; cursor: wait; }

.fichier-box {
  display: flex; align-items: center; gap: 4px;
  background: #f5f2fb; border: 1px solid #e4e1ea; border-radius: 12px; padding: 10px 12px;
}
.fichier-nom { font-size: 0.85rem; font-weight: 600; color: #1f2933; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.fichier-meta { font-size: 0.72rem; color: #767683; }

.recap-tuile {
  display: flex;
  align-items: flex-start;
  background: #f7f8fb;
  border: 1px solid #eceff4;
  border-radius: 12px;
  padding: 14px 16px;
  height: 100%;
}
.recap-label {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: #6b7785;
  font-weight: 600;
}
.recap-valeur { font-size: 15px; font-weight: 600; color: #1f2933; }

.piece-ligne {
  display: flex; align-items: center;
  background: #f5f2fb; border: 1px solid #e4e1ea; border-radius: 10px;
  padding: 10px 14px; font-size: 0.9rem; color: #1f2933;
}
</style>
