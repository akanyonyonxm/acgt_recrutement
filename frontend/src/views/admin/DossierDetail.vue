<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import api from '../../api'
import StatutBadge from '../../components/StatutBadge.vue'
import { couleurStatut } from '../../statuts'

const route = useRoute()
const id = route.params.id

const dossier = ref(null)
const historique = ref([])
const snack = ref({ show: false, color: 'success', text: '' })

const q = ref('')
const resultats = ref([])
const ligneChoisie = ref(null)

const motifRejet = ref('')
const dialogRejet = ref(false)
const motifNonRetenu = ref('')
const dialogNonRetenir = ref(false)

const evaluateurs = ref([])
const affectations = ref([])
const evaluations = ref([])
const evalChoisi = ref(null)
const peutValider = ref(true)

const estDepose = computed(() => dossier.value?.statut === 'depose')
const estEnExamen = computed(() => dossier.value?.statut === 'en_examen')

function notifier(text, color = 'success') {
  snack.value = { show: true, color, text }
}

// Confirmation réutilisable pour les actions sensibles (approuver, retenir...).
const confirmation = ref({ show: false, titre: '', message: '', couleur: 'primary', action: null })
function demanderConfirmation(titre, message, action, couleur = 'primary') {
  confirmation.value = { show: true, titre, message, couleur, action }
}
function confirmer() {
  const a = confirmation.value.action
  confirmation.value.show = false
  if (a) a()
}

async function charger() {
  const { data } = await api.get(`/dossiers/${id}/`)
  dossier.value = data
  q.value = data.nom
  historique.value = (await api.get(`/dossiers/${id}/historique/`)).data
  if (['en_examen', 'retenu', 'non_retenu'].includes(data.statut)) await chargerExamen()
}

async function chercherEligibilite() {
  const { data } = await api.get('/eligibilite/', { params: { q: q.value } })
  resultats.value = data.results
}

async function chargerExamen() {
  const [a, e, ev] = await Promise.all([
    api.get(`/dossiers/${id}/affectations/`),
    api.get(`/dossiers/${id}/evaluations/`),
    api.get('/auth/evaluateurs/'),
  ])
  affectations.value = a.data
  evaluations.value = e.data
  evaluateurs.value = ev.data.map((u) => ({ value: u.id, title: u.nom }))
}

async function action(verbe, corps) {
  try {
    await api.post(`/dossiers/${id}/${verbe}/`, corps || {})
    notifier('Action effectuée.')
    dialogRejet.value = false
    await charger()
  } catch (e) {
    notifier(e.response?.data?.detail || e.response?.data?.motif || 'Action impossible.', 'error')
  }
}

const approuver = () => action('approuver', ligneChoisie.value ? { eligibilite_id: ligneChoisie.value } : {})
function rejeter() {
  if (!motifRejet.value.trim()) return notifier('Le motif est obligatoire.', 'error')
  action('rejeter', { motif: motifRejet.value })
}
const retenir = () => action('retenir')
function nonRetenir() {
  if (!motifNonRetenu.value.trim()) return notifier('Le motif est obligatoire.', 'error')
  action('non-retenir', { motif: motifNonRetenu.value })
}

async function affecter() {
  if (!evalChoisi.value) return
  await api.post(`/dossiers/${id}/affectations/`, { evaluateur_id: evalChoisi.value, peut_valider: peutValider.value })
  evalChoisi.value = null
  await chargerExamen()
}
async function retirerAffectation(evId) {
  await api.delete(`/dossiers/${id}/affectations/${evId}/`)
  await chargerExamen()
}

const ICONE_PIECE = {
  cv: 'mdi-file-account', identite: 'mdi-card-account-details',
  diplome: 'mdi-school', attestation_stage: 'mdi-certificate',
}
const iconePiece = (code) => ICONE_PIECE[code] || 'mdi-file-document'

// Aperçu des pièces (PDF/image) avec navigation.
const apercu = ref({ show: false, index: 0 })
const pieceCourante = computed(() => dossier.value?.pieces?.[apercu.value.index] || null)
const estImage = (p) => /\.(png|jpe?g|gif|webp|bmp)$/i.test(p?.nom_original || '')
const urlPiece = (p, inline) =>
  `/api/dossiers/${id}/pieces/${p.id}/telecharger/${inline ? '?inline=1' : ''}`
function ouvrirApercu(i) { apercu.value = { show: true, index: i } }
function naviguer(d) {
  const n = dossier.value.pieces.length
  apercu.value.index = (apercu.value.index + d + n) % n
}
const dateFr = (d) => new Date(d).toLocaleString('fr-FR')
const kos = (o) => `${Math.round(o / 1024)} Ko`
onMounted(charger)
</script>

<template>
  <div v-if="dossier">
    <v-btn variant="text" color="primary" prepend-icon="mdi-arrow-left"
           :to="{ name: 'validation' }" class="mb-2">Retour</v-btn>

    <v-card flat class="entete-dossier mb-6">
      <div class="d-flex align-center flex-wrap ga-4 pa-5">
        <v-avatar color="white" size="56" class="elevation-3">
          <v-icon color="primary" size="30">mdi-account</v-icon>
        </v-avatar>
        <div class="flex-grow-1" style="min-width: 200px">
          <div class="ref-dossier">DOSSIER {{ dossier.code || ('#' + dossier.id) }}</div>
          <h1 class="nom-candidat">{{ dossier.nom }} {{ dossier.postnom }} {{ dossier.prenom }}</h1>
          <div class="meta-dossier">
            <v-icon size="14">mdi-bullhorn-outline</v-icon>{{ dossier.appel_titre }}
            <template v-if="dossier.poste_libelle">
              <span class="sep">·</span><v-icon size="14">mdi-briefcase-outline</v-icon>{{ dossier.poste_libelle }}
            </template>
          </div>
        </div>
        <StatutBadge :statut="dossier.statut" :libelle="dossier.statut_libelle" />
      </div>
    </v-card>

    <v-row>
      <!-- Colonne gauche : infos + pièces -->
      <v-col cols="12" md="6">
        <v-card flat border class="mb-4">
          <v-card-title class="text-subtitle-1 font-weight-bold">Informations</v-card-title>
          <v-divider />
          <div class="pa-4">
            <div class="info-tuile">
              <v-icon color="primary" class="mr-3">mdi-identifier</v-icon>
              <div><div class="info-label">Code du dossier</div><div class="info-valeur">{{ dossier.code || '—' }}</div></div>
            </div>
            <div class="info-tuile">
              <v-icon color="primary" class="mr-3">mdi-bullhorn-outline</v-icon>
              <div><div class="info-label">Appel</div><div class="info-valeur">{{ dossier.appel_titre }}</div></div>
            </div>
            <div class="info-tuile">
              <v-icon color="primary" class="mr-3">mdi-briefcase-outline</v-icon>
              <div><div class="info-label">Poste visé</div><div class="info-valeur">{{ dossier.poste_libelle || '—' }}</div></div>
            </div>
            <div class="info-tuile">
              <v-icon color="primary" class="mr-3">mdi-email-outline</v-icon>
              <div><div class="info-label">Email de contact</div><div class="info-valeur">{{ dossier.email }}</div></div>
            </div>
            <div class="info-tuile">
              <v-icon color="primary" class="mr-3">mdi-account-outline</v-icon>
              <div><div class="info-label">Déposé par</div><div class="info-valeur">{{ dossier.deposant }}</div></div>
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
            <v-list-item v-for="(p, i) in dossier.pieces" :key="p.id"
                         :title="p.type_piece.libelle"
                         :subtitle="`${kos(p.taille)} · ${p.nom_original}`"
                         @click="ouvrirApercu(i)" style="cursor:pointer">
              <template #prepend>
                <v-avatar color="primary" variant="tonal" rounded="lg" size="40">
                  <v-icon>{{ iconePiece(p.type_piece.code) }}</v-icon>
                </v-avatar>
              </template>
              <template #append>
                <v-btn icon="mdi-eye-outline" variant="text" color="primary" size="small"
                       @click.stop="ouvrirApercu(i)" />
                <v-btn icon="mdi-download" variant="text" color="primary" size="small"
                       :href="`/api/dossiers/${dossier.id}/pieces/${p.id}/telecharger/`" target="_blank" @click.stop />
              </template>
            </v-list-item>
            <v-list-item v-if="!dossier.pieces.length" class="text-medium-emphasis">Aucune pièce.</v-list-item>
          </v-list>
        </v-card>
      </v-col>

      <!-- Colonne droite : actions selon statut -->
      <v-col cols="12" md="6">
        <!-- DÉPOSÉ -->
        <v-card v-if="estDepose" flat border class="mb-4">
          <v-card-title class="text-subtitle-1 font-weight-bold d-flex align-center">
            <v-icon color="primary" class="mr-2">mdi-account-search</v-icon> Vérifier l'éligibilité
          </v-card-title>
          <v-divider />
          <v-card-text>
            <v-text-field v-model="q" label="Rechercher un nom dans la liste"
                          append-inner-icon="mdi-magnify" hide-details
                          @click:append-inner="chercherEligibilite" @keyup.enter="chercherEligibilite" />
            <v-list class="mt-2" density="compact">
              <v-list-item v-for="r in resultats" :key="r.id"
                           :active="ligneChoisie === r.id" color="success"
                           @click="ligneChoisie = r.id" rounded="lg">
                <v-list-item-title>
                  <strong>{{ r.nom }}</strong> {{ r.postnom }} {{ r.prenom }}
                </v-list-item-title>
                <v-list-item-subtitle>
                  Code : {{ r.code || '—' }}
                </v-list-item-subtitle>
              </v-list-item>
              <v-list-item v-if="!resultats.length" class="text-medium-emphasis">
                Recherchez puis sélectionnez la personne dans la liste d'éligibilité.
              </v-list-item>
            </v-list>
            <v-alert v-if="ligneChoisie" type="success" variant="tonal" density="compact" class="mt-2">
              Rattachement sélectionné.
              <a href="#" @click.prevent="ligneChoisie = null"> retirer</a>
            </v-alert>
          </v-card-text>
          <v-divider />
          <v-alert v-if="!ligneChoisie" type="info" variant="tonal" density="compact" class="ma-4 mb-0">
            Sélectionnez d'abord la personne dans la liste d'éligibilité pour pouvoir décider.
          </v-alert>
          <v-card-actions class="pa-4">
            <v-btn color="success" variant="flat" prepend-icon="mdi-check" :disabled="!ligneChoisie"
                   @click="demanderConfirmation('Approuver le dossier', 'Le dossier passera en examen et le candidat sera notifié par email.', approuver, 'success')">
              Approuver → examen
            </v-btn>
            <v-spacer />
            <v-btn color="error" variant="outlined" prepend-icon="mdi-close" :disabled="!ligneChoisie"
                   @click="dialogRejet = true">
              Rejeter
            </v-btn>
          </v-card-actions>
        </v-card>

        <!-- EN EXAMEN : désignation -->
        <v-card v-if="estEnExamen" flat border class="mb-4">
          <v-card-title class="text-subtitle-1 font-weight-bold d-flex align-center">
            <v-icon color="primary" class="mr-2">mdi-account-tie</v-icon> Évaluateurs désignés
          </v-card-title>
          <v-divider />
          <v-list>
            <v-list-item v-for="a in affectations" :key="a.id" :title="a.evaluateur">
              <template #prepend><v-icon color="primary">mdi-account-tie</v-icon></template>
              <template #append>
                <v-chip :color="a.peut_valider ? 'success' : 'grey'" size="small" variant="tonal" class="mr-2">
                  {{ a.peut_valider ? 'peut valider' : 'consultation' }}
                </v-chip>
                <v-btn icon="mdi-close" variant="text" size="x-small" @click="retirerAffectation(a.evaluateur_id)" />
              </template>
            </v-list-item>
            <v-list-item v-if="!affectations.length" class="text-medium-emphasis">Aucun évaluateur désigné.</v-list-item>
          </v-list>
          <v-divider />
          <v-card-text>
            <v-row dense align="center">
              <v-col cols="12" sm="6">
                <v-select v-model="evalChoisi" :items="evaluateurs" label="Évaluateur" hide-details clearable />
              </v-col>
              <v-col cols="auto"><v-switch v-model="peutValider" label="peut valider" color="success" hide-details /></v-col>
              <v-col cols="auto">
                <v-btn color="primary" :disabled="!evalChoisi" prepend-icon="mdi-account-plus" @click="affecter">Désigner</v-btn>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>

        <!-- EN EXAMEN : décision finale (l'admin tranche) -->
        <v-card v-if="estEnExamen" flat border class="mb-4">
          <v-card-title class="text-subtitle-1 font-weight-bold d-flex align-center">
            <v-icon color="primary" class="mr-2">mdi-gavel</v-icon> Décision finale
          </v-card-title>
          <v-divider />
          <v-card-text class="text-body-2 text-medium-emphasis">
            Tranche définitive du dossier (notifie le candidat par email). À faire après
            consultation des avis ci-dessous.
          </v-card-text>
          <v-card-actions class="px-4 pb-4">
            <v-btn color="success" variant="flat" prepend-icon="mdi-check-bold"
                   @click="demanderConfirmation('Retenir le candidat', 'Décision définitive : le candidat passera en « retenu » et sera notifié par email.', retenir, 'success')">
              Retenir
            </v-btn>
            <v-spacer />
            <v-btn color="error" variant="outlined" prepend-icon="mdi-close-thick"
                   @click="dialogNonRetenir = true">Non retenir</v-btn>
          </v-card-actions>
        </v-card>

        <!-- Avis -->
        <v-card v-if="evaluations.length" flat border class="mb-4">
          <v-card-title class="text-subtitle-1 font-weight-bold d-flex align-center">
            <v-icon color="primary" class="mr-2">mdi-comment-check-outline</v-icon> Avis des évaluateurs
          </v-card-title>
          <v-divider />
          <v-list>
            <v-list-item v-for="e in evaluations" :key="e.id" :title="e.evaluateur" :subtitle="e.avis || '—'">
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
                <div class="font-weight-medium">
                  {{ h.ancien_statut_libelle }} → {{ h.nouveau_statut_libelle }}
                </div>
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

    <!-- Dialog rejet -->
    <v-dialog v-model="dialogRejet" max-width="480">
      <v-card>
        <v-card-title class="bg-error text-white d-flex align-center">
          <v-icon class="mr-2">mdi-close-circle</v-icon>Rejeter le dossier
        </v-card-title>
        <v-card-text class="pt-4">
          <v-textarea v-model="motifRejet" label="Commentaire de rejet (obligatoire)" rows="3"
                      hint="Visible dans l'historique et envoyé au candidat" persistent-hint autofocus />
        </v-card-text>
        <v-card-actions class="pa-4 pt-0">
          <v-spacer />
          <v-btn variant="outlined" @click="dialogRejet = false">Annuler</v-btn>
          <v-btn color="error" variant="flat" @click="rejeter">Confirmer le rejet</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Dialog non-retenir -->
    <v-dialog v-model="dialogNonRetenir" max-width="480">
      <v-card>
        <v-card-title class="bg-error text-white d-flex align-center">
          <v-icon class="mr-2">mdi-close-circle</v-icon>Non retenir le dossier
        </v-card-title>
        <v-card-text class="pt-4">
          <v-textarea v-model="motifNonRetenu" label="Motif (obligatoire)" rows="3" autofocus />
        </v-card-text>
        <v-card-actions class="pa-4 pt-0">
          <v-spacer />
          <v-btn variant="outlined" @click="dialogNonRetenir = false">Annuler</v-btn>
          <v-btn color="error" variant="flat" @click="nonRetenir">Confirmer</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Confirmation générique (approuver, retenir) -->
    <v-dialog v-model="confirmation.show" max-width="440">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon :color="confirmation.couleur" class="mr-2">mdi-help-circle-outline</v-icon>
          {{ confirmation.titre }}
        </v-card-title>
        <v-card-text>{{ confirmation.message }}</v-card-text>
        <v-card-actions class="pa-4 pt-0">
          <v-spacer />
          <v-btn variant="text" @click="confirmation.show = false">Annuler</v-btn>
          <v-btn :color="confirmation.couleur" variant="flat" @click="confirmer">Confirmer</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Aperçu des pièces (PDF / image) avec navigation -->
    <v-dialog v-model="apercu.show" max-width="980" scrollable>
      <v-card v-if="pieceCourante" flat>
        <v-card-title class="d-flex align-center ga-2 py-3">
          <v-icon color="primary">{{ iconePiece(pieceCourante.type_piece.code) }}</v-icon>
          <div class="flex-grow-1" style="min-width:0">
            <div class="font-weight-bold">{{ pieceCourante.type_piece.libelle }}</div>
            <div class="text-caption text-medium-emphasis text-truncate">{{ pieceCourante.nom_original }}</div>
          </div>
          <v-chip size="small" variant="tonal">{{ apercu.index + 1 }} / {{ dossier.pieces.length }}</v-chip>
          <v-btn icon="mdi-download" variant="text" size="small"
                 :href="urlPiece(pieceCourante, false)" target="_blank" />
          <v-btn icon="mdi-close" variant="text" size="small" @click="apercu.show = false" />
        </v-card-title>
        <v-divider />
        <div class="apercu-zone">
          <v-btn icon="mdi-chevron-left" variant="elevated" class="nav-btn nav-gauche"
                 :disabled="dossier.pieces.length < 2" @click="naviguer(-1)" />
          <img v-if="estImage(pieceCourante)" :src="urlPiece(pieceCourante, true)" class="apercu-img" alt="" />
          <iframe v-else :src="urlPiece(pieceCourante, true)" class="apercu-iframe" title="aperçu" />
          <v-btn icon="mdi-chevron-right" variant="elevated" class="nav-btn nav-droite"
                 :disabled="dossier.pieces.length < 2" @click="naviguer(1)" />
        </div>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snack.show" :color="snack.color" timeout="3000">{{ snack.text }}</v-snackbar>
  </div>
</template>

<style scoped>
.entete-dossier {
  background: linear-gradient(135deg, #1a237e 0%, #0d1b2a 100%) !important;
  border-radius: 16px !important;
}
.ref-dossier { font-size: 0.72rem; font-weight: 700; letter-spacing: 0.08em; color: #bdc2ff; text-transform: uppercase; }
.nom-candidat { font-size: 1.5rem; font-weight: 800; color: #fff; line-height: 1.2; }
.meta-dossier { font-size: 0.85rem; color: #c5cae9; margin-top: 5px; display: flex; align-items: center; gap: 5px; flex-wrap: wrap; }
.meta-dossier .sep { opacity: 0.6; }

.info-tuile {
  display: flex;
  align-items: flex-start;
  background: #f7f8fb;
  border: 1px solid #eceff4;
  border-radius: 12px;
  padding: 12px 14px;
}
.info-tuile + .info-tuile { margin-top: 10px; }
.info-label {
  font-size: 11px; text-transform: uppercase; letter-spacing: 0.03em;
  color: #6b7785; font-weight: 600;
}
.info-valeur { font-size: 14px; font-weight: 600; color: #1f2933; }

/* Aperçu des pièces */
.apercu-zone { position: relative; background: #2b2b2b; display: flex; align-items: center; justify-content: center; height: 72vh; overflow: auto; }
.apercu-iframe { width: 100%; height: 100%; border: none; background: #fff; }
.apercu-img { max-width: 100%; max-height: 100%; object-fit: contain; }
.nav-btn { position: absolute; top: 50%; transform: translateY(-50%); z-index: 2; opacity: 0.92; }
.nav-gauche { left: 12px; }
.nav-droite { right: 12px; }
</style>
