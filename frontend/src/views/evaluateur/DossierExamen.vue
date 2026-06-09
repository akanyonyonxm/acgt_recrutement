<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../../api'
import { useAuthStore } from '../../stores/auth'
import StatutBadge from '../../components/StatutBadge.vue'
import { couleurStatut } from '../../statuts'

const route = useRoute()
const auth = useAuthStore()
const id = route.params.id

const dossier = ref(null)
const evaluations = ref([])
const affectations = ref([])
const historique = ref([])
const snack = ref({ show: false, color: 'success', text: '' })

// Saisie de l'avis
const monAvis = ref({ avis: '', recommandation: 'reserve' })
const enregistrement = ref(false)

// Décision
const dialogNonRetenir = ref(false)
const motif = ref('')
const enDecision = ref(false)

const RECOMMANDATIONS = [
  { value: 'retenu', title: 'Favorable — retenu' },
  { value: 'non_retenu', title: 'Défavorable — non retenu' },
  { value: 'reserve', title: 'Réservé' },
]

const estEnExamen = computed(() => dossier.value?.statut === 'en_examen')
// L'évaluateur peut trancher s'il est désigné « peut_valider », ou s'il est admin.
const peutValider = computed(() => {
  if (auth.estAdmin) return true
  const moi = affectations.value.find((a) => a.evaluateur_id === auth.utilisateur?.id)
  return !!moi?.peut_valider
})
const autresAvis = computed(() =>
  evaluations.value.filter((e) => e.evaluateur !== auth.utilisateur?.email)
)

function notifier(text, color = 'success') { snack.value = { show: true, color, text } }

async function charger() {
  const { data } = await api.get(`/dossiers/${id}/`)
  dossier.value = data
  const [ev, af, hi] = await Promise.all([
    api.get(`/dossiers/${id}/evaluations/`),
    api.get(`/dossiers/${id}/affectations/`),
    api.get(`/dossiers/${id}/historique/`),
  ])
  evaluations.value = ev.data
  affectations.value = af.data
  historique.value = hi.data
  // Pré-remplit le formulaire avec mon avis existant, le cas échéant.
  const mien = ev.data.find((e) => e.evaluateur === auth.utilisateur?.email)
  if (mien) monAvis.value = { avis: mien.avis || '', recommandation: mien.recommandation }
}

async function enregistrerAvis() {
  enregistrement.value = true
  try {
    await api.post(`/dossiers/${id}/evaluations/`, monAvis.value)
    notifier('Avis enregistré.')
    await charger()
  } catch (e) {
    notifier(e.response?.data?.detail || 'Enregistrement impossible.', 'error')
  } finally {
    enregistrement.value = false
  }
}

async function decider(verbe, corps) {
  enDecision.value = true
  try {
    await api.post(`/dossiers/${id}/${verbe}/`, corps || {})
    notifier('Décision enregistrée.')
    dialogNonRetenir.value = false
    await charger()
  } catch (e) {
    notifier(e.response?.data?.detail || e.response?.data?.motif || 'Action impossible.', 'error')
  } finally {
    enDecision.value = false
  }
}
function retenir() { decider('retenir') }
function nonRetenir() {
  if (!motif.value.trim()) return notifier('Le motif est obligatoire.', 'error')
  decider('non-retenir', { motif: motif.value })
}

const ICONE_PIECE = {
  cv: 'mdi-file-account', identite: 'mdi-card-account-details',
  diplome: 'mdi-school', attestation_stage: 'mdi-certificate',
}
const iconePiece = (code) => ICONE_PIECE[code] || 'mdi-file-document'
const dateFr = (d) => new Date(d).toLocaleString('fr-FR')
const kos = (o) => `${Math.round(o / 1024)} Ko`
onMounted(charger)
</script>

<template>
  <div v-if="dossier">
    <v-btn variant="text" color="primary" prepend-icon="mdi-arrow-left"
           :to="{ name: 'eval-dossiers' }" class="mb-2">Retour</v-btn>

    <div class="d-flex align-center mb-6 flex-wrap ga-3">
      <v-avatar color="primary" variant="tonal" rounded="lg" size="44" class="mr-1">
        <v-icon>mdi-file-account-outline</v-icon>
      </v-avatar>
      <div>
        <h1 class="text-h5 font-weight-bold text-primary" style="line-height:1.2">Dossier #{{ dossier.id }}</h1>
        <div class="text-body-1">{{ dossier.nom }} {{ dossier.postnom }} {{ dossier.prenom }}</div>
      </div>
      <v-spacer />
      <StatutBadge :statut="dossier.statut" :libelle="dossier.statut_libelle" />
    </div>

    <v-row>
      <!-- Gauche : infos + pièces -->
      <v-col cols="12" md="6">
        <v-card flat border class="mb-4">
          <v-card-title class="text-subtitle-1 font-weight-bold">Informations</v-card-title>
          <v-divider />
          <div class="pa-4">
            <div class="info-tuile">
              <v-icon color="primary" class="mr-3">mdi-bullhorn-outline</v-icon>
              <div><div class="info-label">Appel</div><div class="info-valeur">{{ dossier.appel_titre }}</div></div>
            </div>
            <div class="info-tuile">
              <v-icon color="primary" class="mr-3">mdi-briefcase-outline</v-icon>
              <div><div class="info-label">Poste visé</div><div class="info-valeur">{{ dossier.poste_libelle || '—' }}</div></div>
            </div>
            <div v-if="dossier.ligne_eligibilite" class="info-tuile" style="border-color:#388E3C;background:#f4faf6">
              <v-icon color="success" class="mr-3">mdi-link-variant</v-icon>
              <div><div class="info-label">Éligibilité rattachée</div>
                <div class="info-valeur">{{ dossier.ligne_eligibilite }}</div></div>
            </div>
          </div>
        </v-card>

        <v-card flat border>
          <v-card-title class="text-subtitle-1 font-weight-bold d-flex align-center">
            <v-icon color="primary" class="mr-2">mdi-paperclip</v-icon> Pièces jointes
            <v-chip size="x-small" class="ml-2" color="primary" variant="tonal">{{ dossier.pieces.length }}</v-chip>
          </v-card-title>
          <v-divider />
          <v-list>
            <v-list-item v-for="p in dossier.pieces" :key="p.id"
                         :title="p.type_piece.libelle" :subtitle="`${kos(p.taille)} · ${p.nom_original}`">
              <template #prepend>
                <v-avatar color="primary" variant="tonal" rounded="lg" size="40">
                  <v-icon>{{ iconePiece(p.type_piece.code) }}</v-icon>
                </v-avatar>
              </template>
              <template #append>
                <v-btn icon="mdi-download" variant="tonal" color="primary" size="small"
                       :href="`/api/dossiers/${dossier.id}/pieces/${p.id}/telecharger/`" target="_blank" />
              </template>
            </v-list-item>
            <v-list-item v-if="!dossier.pieces.length" class="text-medium-emphasis">Aucune pièce.</v-list-item>
          </v-list>
        </v-card>
      </v-col>

      <!-- Droite : mon avis + décision + autres avis + historique -->
      <v-col cols="12" md="6">
        <!-- Mon avis -->
        <v-card flat border class="mb-4">
          <v-card-title class="text-subtitle-1 font-weight-bold d-flex align-center">
            <v-icon color="primary" class="mr-2">mdi-comment-edit-outline</v-icon> Mon avis
          </v-card-title>
          <v-divider />
          <v-card-text>
            <v-select v-model="monAvis.recommandation" :items="RECOMMANDATIONS"
                      label="Recommandation" variant="outlined" density="comfortable"
                      :disabled="!estEnExamen" class="mb-2" />
            <v-textarea v-model="monAvis.avis" label="Commentaire (facultatif)" rows="4"
                        variant="outlined" :disabled="!estEnExamen" hide-details />
          </v-card-text>
          <v-card-actions v-if="estEnExamen" class="px-4 pb-4">
            <v-spacer />
            <v-btn color="primary" variant="flat" prepend-icon="mdi-content-save"
                   :loading="enregistrement" @click="enregistrerAvis">Enregistrer mon avis</v-btn>
          </v-card-actions>
          <v-alert v-else type="info" variant="tonal" density="compact" class="ma-4 mt-0">
            Ce dossier n'est plus en examen : l'avis n'est plus modifiable.
          </v-alert>
        </v-card>

        <!-- Décision (si autorisé) -->
        <v-card v-if="estEnExamen && peutValider" flat border class="mb-4">
          <v-card-title class="text-subtitle-1 font-weight-bold d-flex align-center">
            <v-icon color="primary" class="mr-2">mdi-gavel</v-icon> Décision
          </v-card-title>
          <v-divider />
          <v-card-text class="text-body-2 text-medium-emphasis">
            Tranche définitive de ce dossier (notifie le candidat par email).
          </v-card-text>
          <v-card-actions class="px-4 pb-4">
            <v-btn color="success" variant="flat" prepend-icon="mdi-check-bold"
                   :loading="enDecision" @click="retenir">Retenir</v-btn>
            <v-spacer />
            <v-btn color="error" variant="outlined" prepend-icon="mdi-close-thick"
                   @click="dialogNonRetenir = true">Non retenir</v-btn>
          </v-card-actions>
        </v-card>

        <!-- Autres avis -->
        <v-card v-if="autresAvis.length" flat border class="mb-4">
          <v-card-title class="text-subtitle-1 font-weight-bold d-flex align-center">
            <v-icon color="primary" class="mr-2">mdi-account-group-outline</v-icon> Avis des autres évaluateurs
          </v-card-title>
          <v-divider />
          <v-list>
            <v-list-item v-for="e in autresAvis" :key="e.id" :title="e.evaluateur" :subtitle="e.avis || '—'">
              <template #append>
                <v-chip :color="couleurStatut(e.recommandation)" size="small" variant="tonal">
                  {{ e.recommandation_libelle }}
                </v-chip>
              </template>
            </v-list-item>
          </v-list>
        </v-card>

        <!-- Historique -->
        <v-card flat border>
          <v-card-title class="text-subtitle-1 font-weight-bold d-flex align-center">
            <v-icon color="primary" class="mr-2">mdi-history</v-icon> Historique
          </v-card-title>
          <v-divider />
          <div class="pa-5">
            <v-timeline side="end" align="start" density="comfortable" truncate-line="both">
              <v-timeline-item v-for="h in historique" :key="h.id" size="x-small" dot-color="primary">
                <div class="font-weight-medium">{{ h.ancien_statut_libelle }} → {{ h.nouveau_statut_libelle }}</div>
                <div class="text-caption text-medium-emphasis">
                  {{ dateFr(h.horodatage) }}<span v-if="h.par"> · {{ h.par }}</span>
                  <span v-if="h.motif"> · {{ h.motif }}</span>
                </div>
              </v-timeline-item>
            </v-timeline>
          </div>
        </v-card>
      </v-col>
    </v-row>

    <!-- Dialog non-retenir -->
    <v-dialog v-model="dialogNonRetenir" max-width="480">
      <v-card>
        <v-card-title class="bg-error text-white d-flex align-center">
          <v-icon class="mr-2">mdi-close-circle</v-icon>Non retenir le dossier
        </v-card-title>
        <v-card-text class="pt-4">
          <v-textarea v-model="motif" label="Motif (obligatoire)" rows="3" autofocus />
        </v-card-text>
        <v-card-actions class="pa-4 pt-0">
          <v-spacer />
          <v-btn variant="outlined" @click="dialogNonRetenir = false">Annuler</v-btn>
          <v-btn color="error" variant="flat" :loading="enDecision" @click="nonRetenir">Confirmer</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snack.show" :color="snack.color" timeout="3000">{{ snack.text }}</v-snackbar>
  </div>
</template>

<style scoped>
.info-tuile { display: flex; align-items: flex-start; background: #f7f8fb; border: 1px solid #eceff4; border-radius: 12px; padding: 12px 14px; }
.info-tuile + .info-tuile { margin-top: 10px; }
.info-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.03em; color: #6b7785; font-weight: 600; }
.info-valeur { font-size: 14px; font-weight: 600; color: #1f2933; }
</style>
