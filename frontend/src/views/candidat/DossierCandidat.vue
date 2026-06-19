<script setup>
import { ref, onMounted, computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import api from '../../api'
import StatutBadge from '../../components/StatutBadge.vue'

const route = useRoute()
const dossier = ref(null)
const historique = ref([])

const ETAPES = [
  { label: 'Déposé', icon: 'mdi-inbox-arrow-down' },
  { label: 'En examen', icon: 'mdi-magnify-scan' },
  { label: 'Décision', icon: 'mdi-flag-checkered' },
]
const ordre = { brouillon: 0, depose: 1, en_examen: 2, retenu: 3, non_retenu: 3, rejete: 3 }
const niveau = computed(() => ordre[dossier.value?.statut] ?? 0)
const refuse = computed(() => ['non_retenu', 'rejete'].includes(dossier.value?.statut))
const retenu = computed(() => dossier.value?.statut === 'retenu')

// Le candidat ne voit que le PREMIER (Brouillon → Déposé) et le DERNIER statut
// (décision finale) — jamais les étapes intermédiaires. L'historique arrive du
// plus récent au plus ancien : on garde donc le 1er (décision) et le dernier (dépôt).
const historiqueAffiche = computed(() => {
  const h = historique.value
  return h.length <= 2 ? h : [h[0], h[h.length - 1]]
})

const ICONE_PIECE = {
  cv: 'mdi-file-account', identite: 'mdi-card-account-details',
  diplome: 'mdi-school', attestation_stage: 'mdi-certificate',
}
const iconePiece = (code) => ICONE_PIECE[code] || 'mdi-file-document'

onMounted(async () => {
  const { data } = await api.get(`/dossiers/${route.params.id}/`)
  dossier.value = data
  historique.value = (await api.get(`/dossiers/${route.params.id}/historique/`)).data
})
const dateFr = (d) => new Date(d).toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' })
const dateHeure = (d) => new Date(d).toLocaleString('fr-FR')
const kos = (o) => (o > 1048576 ? (o / 1048576).toFixed(1) + ' Mo' : Math.round(o / 1024) + ' Ko')
</script>

<template>
  <v-container v-if="dossier" class="py-6 px-6" style="max-width: 1200px">
    <!-- Fil d'ariane -->
    <div class="text-caption text-medium-emphasis mb-2">
      <RouterLink :to="{ name: 'mes-dossiers' }" class="text-medium-emphasis">Mes dossiers</RouterLink>
      › Dossier #{{ dossier.id }}
    </div>

    <!-- En-tête -->
    <div class="d-flex align-start flex-wrap ga-3 mb-5">
      <div>
        <h1 class="text-h4 font-weight-bold text-primary">{{ dossier.poste_libelle || (dossier.nom + ' ' + dossier.prenom) }}</h1>
        <div class="text-body-2 text-medium-emphasis">
          Dossier {{ dossier.code || ('#' + dossier.id) }} · {{ dossier.appel_titre }} · déposé le {{ dateFr(dossier.cree_le) }}
        </div>
      </div>
      <v-spacer />
      <StatutBadge :statut="dossier.statut" :libelle="dossier.statut_libelle" />
      <v-btn v-if="dossier.statut === 'brouillon'" color="accent" class="text-primary font-weight-bold"
             prepend-icon="mdi-pencil" :to="{ name: 'postuler', query: { dossier: dossier.id } }">
        Modifier le dossier
      </v-btn>
    </div>

    <!-- Frise de statut -->
    <v-card flat border class="pa-6 mb-5">
      <div class="text-subtitle-2 font-weight-bold text-medium-emphasis mb-5">STATUT DE LA CANDIDATURE</div>
      <div class="frise">
        <template v-for="(e, i) in ETAPES" :key="i">
          <div class="frise-step">
            <div class="frise-cercle" :class="{ actif: niveau >= i + 1, refus: refuse && i === 2 }">
              <v-icon color="white" size="22">{{ refuse && i === 2 ? 'mdi-close' : e.icon }}</v-icon>
            </div>
            <div class="frise-label" :class="{ 'text-primary font-weight-bold': niveau >= i + 1 }">
              {{ i === 2 && retenu ? 'Retenu' : (i === 2 && refuse ? dossier.statut_libelle : e.label) }}
            </div>
          </div>
          <div v-if="i < ETAPES.length - 1" class="frise-line" :class="{ done: niveau >= i + 2 }"></div>
        </template>
      </div>
    </v-card>

    <v-row>
      <!-- Colonne gauche -->
      <v-col cols="12" md="7">
        <!-- Historique -->
        <v-card flat border class="mb-5">
          <v-card-title class="text-subtitle-1 font-weight-bold d-flex align-center">
            <v-icon color="primary" class="mr-2">mdi-history</v-icon> Historique du dossier
          </v-card-title>
          <v-divider />
          <div class="pa-5">
            <v-timeline side="end" align="start" density="comfortable" truncate-line="both">
              <v-timeline-item v-for="h in historiqueAffiche" :key="h.id" size="x-small" dot-color="primary">
                <div class="font-weight-medium">{{ h.ancien_statut_libelle }} → {{ h.nouveau_statut_libelle }}</div>
                <div class="text-caption text-medium-emphasis">
                  {{ dateHeure(h.horodatage) }}<span v-if="h.motif"> · {{ h.motif }}</span>
                </div>
              </v-timeline-item>
            </v-timeline>
          </div>
        </v-card>

        <!-- Documents transmis -->
        <v-card flat border>
          <v-card-title class="text-subtitle-1 font-weight-bold d-flex align-center">
            <v-icon color="primary" class="mr-2">mdi-file-multiple</v-icon> Documents transmis
            <v-spacer />
            <span class="text-caption text-medium-emphasis">{{ dossier.pieces.length }} fichier(s)</span>
          </v-card-title>
          <v-divider />
          <div class="pa-4 d-flex flex-column ga-3">
            <div v-for="p in dossier.pieces" :key="p.id" class="doc-box">
              <v-avatar color="primary" variant="tonal" rounded="lg" size="40" class="mr-3">
                <v-icon>{{ iconePiece(p.type_piece.code) }}</v-icon>
              </v-avatar>
              <div class="flex-grow-1" style="min-width:0">
                <div class="doc-nom">{{ p.nom_original }}</div>
                <div class="doc-meta">{{ p.type_piece.libelle }} · {{ kos(p.taille) }}</div>
              </div>
              <v-btn icon="mdi-download" variant="text" color="primary" size="small"
                     :href="`/api/dossiers/${dossier.id}/pieces/${p.id}/telecharger/`" target="_blank" />
            </div>
          </div>
        </v-card>
      </v-col>

      <!-- Colonne droite -->
      <v-col cols="12" md="5">
        <v-card flat class="pa-5 mb-4 note" color="primary">
          <div class="text-subtitle-1 font-weight-bold mb-2">Note institutionnelle</div>
          <p class="text-body-2" style="opacity:0.88">
            L'Agence Congolaise des Grands Travaux assure un traitement équitable et transparent de chaque dossier.
            Vous serez notifié(e) par email à chaque évolution de votre candidature.
          </p>
        </v-card>

        <v-card flat border class="pa-5">
          <div class="d-flex align-center mb-4">
            <v-avatar color="primary" size="48" class="mr-3"><v-icon color="white" size="26">mdi-account</v-icon></v-avatar>
            <div>
              <div class="text-subtitle-1 font-weight-bold" style="line-height:1.2">
                {{ dossier.nom }} {{ dossier.postnom }} {{ dossier.prenom }}
              </div>
              <div class="text-caption text-medium-emphasis">Candidat</div>
            </div>
          </div>
          <v-divider class="mb-2" />
          <div class="info-ligne"><span class="info-l">Poste visé</span><span class="info-v">{{ dossier.poste_libelle || '—' }}</span></div>
          <div class="info-ligne"><span class="info-l">Email de contact</span><span class="info-v">{{ dossier.email }}</span></div>
          <div class="info-ligne"><span class="info-l">Déposé par</span><span class="info-v">{{ dossier.deposant }}</span></div>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<style scoped>
.note { color: #fff; }
.frise { display: flex; align-items: flex-start; }
.frise-step { display: flex; flex-direction: column; align-items: center; width: 96px; flex-shrink: 0; }
.frise-cercle { width: 52px; height: 52px; border-radius: 50%; display: flex; align-items: center; justify-content: center; background: #cfd4dc; transition: background 0.3s; }
.frise-cercle.actif { background: #1a237e; }
.frise-cercle.refus { background: #D32F2F; }
.frise-label { margin-top: 8px; font-size: 13px; text-align: center; color: #6b7785; }
.frise-line { flex: 1; height: 4px; margin-top: 24px; border-radius: 2px; background: #e0e3e8; transition: background 0.3s; }
.frise-line.done { background: #1a237e; }

.doc-box { display: flex; align-items: center; background: #f7f8fb; border: 1px solid #eceff4; border-radius: 12px; padding: 10px 12px; height: 100%; transition: background 0.15s, border-color 0.15s; }
.doc-box:hover { background: #f0f3fb; border-color: #c9d4ee; }
.info-ligne { display: flex; justify-content: space-between; gap: 12px; padding: 8px 0; border-bottom: 1px solid #f0f1f4; }
.info-ligne:last-child { border-bottom: none; }
.info-l { font-size: 0.8rem; color: #767683; }
.info-v { font-size: 0.85rem; font-weight: 600; color: #1f2933; text-align: right; word-break: break-word; }
.doc-nom { font-size: 0.85rem; font-weight: 600; color: #1f2933; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.doc-meta { font-size: 0.72rem; color: #767683; }
</style>
