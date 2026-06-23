<script setup>
import { ref, onMounted, computed } from 'vue'
import api from '../../api'
import StatCard from '../../components/StatCard.vue'

const appels = ref([])
const appelId = ref(null)
const rapport = ref(null)
const chargement = ref(false)

const STATUT_DOSSIER = {
  brouillon: { label: 'Brouillon', color: '#90A4AE' },
  depose: { label: 'Déposé', color: '#EF6C00' },
  en_examen: { label: 'En examen', color: '#0288D1' },
  retenu: { label: 'Retenu', color: '#2E7D32' },
  non_retenu: { label: 'Non retenu', color: '#607D8B' },
  rejete: { label: 'Rejeté', color: '#C62828' },
}
const STATUT_RECLAM = {
  en_attente: { label: 'En attente', color: '#EF6C00' },
  validee: { label: 'Validée', color: '#2E7D32' },
  rejetee: { label: 'Rejetée', color: '#C62828' },
}
const COULEURS_POSTE = ['#1a237e', '#0288D1', '#00838F', '#6A1B9A', '#2E7D32', '#EF6C00', '#C62828', '#5D4037', '#455A64', '#AD1457']

async function chargerAppels() {
  const { data } = await api.get('/appels/')
  appels.value = data.results
  if (!appelId.value && appels.value.length) {
    appelId.value = (appels.value.find((a) => a.liste_retenus_publiee) || appels.value[0]).id
  }
}
async function charger() {
  if (!appelId.value) return
  chargement.value = true
  try {
    const { data } = await api.get('/rapports/', { params: { appel: appelId.value } })
    rapport.value = data
  } finally {
    chargement.value = false
  }
}

// --- Helpers graphiques (CSS pur) ---
function donutStyle(segments) {
  const total = segments.reduce((s, x) => s + x.value, 0) || 1
  let acc = 0
  const stops = segments.map((s) => {
    const a = (acc / total) * 360; acc += s.value; const b = (acc / total) * 360
    return `${s.color} ${a}deg ${b}deg`
  })
  return { background: `conic-gradient(${stops.join(', ')})` }
}
const pct = (v, t) => (t ? Math.round((v / t) * 100) : 0)

// --- Données dérivées ---
const r = computed(() => rapport.value)
const segDossiers = computed(() => Object.entries(r.value?.dossiers?.par_statut_en_ligne || {})
  .map(([k, v]) => ({ key: k, label: STATUT_DOSSIER[k]?.label || k, color: STATUT_DOSSIER[k]?.color || '#999', value: v }))
  .filter((s) => s.value > 0))
const totalDossiers = computed(() => segDossiers.value.reduce((s, x) => s + x.value, 0))
const segReclam = computed(() => Object.entries(r.value?.reclamations?.par_statut || {})
  .map(([k, v]) => ({ key: k, label: STATUT_RECLAM[k]?.label || k, color: STATUT_RECLAM[k]?.color || '#999', value: v }))
  .filter((s) => s.value > 0))
const totalReclam = computed(() => segReclam.value.reduce((s, x) => s + x.value, 0))
const segOrigine = computed(() => {
  const o = r.value?.retenus?.par_origine || {}
  return [
    { label: 'Réclamation', color: '#6A1B9A', value: o.reclamation || 0 },
    { label: 'En ligne', color: '#00838F', value: o.en_ligne || 0 },
  ].filter((s) => s.value > 0)
})
const totalRetenus = computed(() => r.value?.retenus?.total || 0)

const segRecours = computed(() => {
  const rc = r.value?.recours || {}
  return [
    { key: 'en_attente', label: 'En attente', color: '#EF6C00', value: rc.en_attente || 0 },
    { key: 'valide', label: 'Validé', color: '#2E7D32', value: rc.valide || 0 },
    { key: 'rejete', label: 'Rejeté', color: '#C62828', value: rc.rejete || 0 },
  ].filter((s) => s.value > 0)
})
const totalRecours = computed(() => r.value?.recours?.total || 0)

const trDossiers = computed(() => r.value?.traitement?.dossiers || { traite: 0, en_attente: 0, total: 0 })
const trReclam = computed(() => r.value?.traitement?.reclamations || { traite: 0, en_attente: 0, total: 0 })
const trRecours = computed(() => r.value?.traitement?.recours || { traite: 0, en_attente: 0, total: 0 })

const retenusPoste = computed(() => r.value?.retenus?.par_poste || [])
const maxRetenusPoste = computed(() => Math.max(1, ...retenusPoste.value.map((p) => p.n)))
const dossiersPoste = computed(() => r.value?.dossiers?.par_poste || [])
const maxRecusPoste = computed(() => Math.max(1, ...dossiersPoste.value.map((p) => p.recus)))

onMounted(async () => { await chargerAppels(); await charger() })
</script>

<template>
  <div>
    <div class="d-flex align-center flex-wrap ga-3 mb-5">
      <v-icon color="primary" size="30" class="mr-1">mdi-chart-box-outline</v-icon>
      <h1 class="text-h5 font-weight-bold text-primary">Rapports & statistiques</h1>
      <v-spacer />
      <v-select v-model="appelId" @update:modelValue="charger"
                :items="appels.map((a) => ({ value: a.id, title: a.titre + (a.liste_retenus_publiee ? ' — publié' : '') }))"
                label="Appel à candidature" hide-details density="compact" variant="outlined" style="max-width: 380px" />
    </div>

    <template v-if="r">
      <!-- KPI principaux -->
      <v-row dense class="mb-5">
        <v-col cols="6" md="3">
          <StatCard icon="mdi-account-multiple-check" :value="r.eligibles.publies" label="Éligibles publiés"
                    :description="`sur ${r.eligibles.total} au total`" color="#1a237e" />
        </v-col>
        <v-col cols="6" md="3">
          <StatCard icon="mdi-folder-multiple" :value="r.dossiers.en_ligne" label="Déposés en ligne"
                    description="Postés par les candidats (hors brouillon)" color="#EF6C00" />
        </v-col>
        <v-col cols="6" md="3">
          <StatCard icon="mdi-account-alert-outline" :value="r.reclamations.total" label="Réclamations"
                    description="Reçues" color="#6A1B9A" />
        </v-col>
        <v-col cols="6" md="3">
          <StatCard icon="mdi-trophy" :value="r.retenus.total" label="Retenus"
                    description="Candidats retenus" color="#2E7D32" />
        </v-col>
      </v-row>

      <!-- Donuts -->
      <v-row dense class="mb-2">
        <v-col cols="12" md="3">
          <v-card flat border class="pa-5 h-100">
            <div class="carte-titre">Dépôts en ligne par statut</div>
            <div class="donut-zone">
              <div class="donut" :style="donutStyle(segDossiers)">
                <div class="donut-hole"><span class="donut-val">{{ totalDossiers }}</span><span class="donut-lib">en ligne</span></div>
              </div>
              <div class="legende">
                <div v-for="s in segDossiers" :key="s.key" class="legende-l">
                  <span class="pastille" :style="{ background: s.color }" />
                  <span class="flex-grow-1">{{ s.label }}</span>
                  <strong>{{ s.value }}</strong>
                  <span class="text-medium-emphasis ml-1">({{ pct(s.value, totalDossiers) }}%)</span>
                </div>
              </div>
            </div>
          </v-card>
        </v-col>
        <v-col cols="12" md="3">
          <v-card flat border class="pa-5 h-100">
            <div class="carte-titre">Réclamations par statut</div>
            <div class="donut-zone">
              <div class="donut" :style="donutStyle(segReclam)">
                <div class="donut-hole"><span class="donut-val">{{ totalReclam }}</span><span class="donut-lib">réclam.</span></div>
              </div>
              <div class="legende">
                <div v-for="s in segReclam" :key="s.key" class="legende-l">
                  <span class="pastille" :style="{ background: s.color }" />
                  <span class="flex-grow-1">{{ s.label }}</span>
                  <strong>{{ s.value }}</strong>
                  <span class="text-medium-emphasis ml-1">({{ pct(s.value, totalReclam) }}%)</span>
                </div>
                <div v-if="!segReclam.length" class="text-medium-emphasis text-caption">Aucune réclamation.</div>
              </div>
            </div>
          </v-card>
        </v-col>
        <v-col cols="12" md="3">
          <v-card flat border class="pa-5 h-100">
            <div class="carte-titre">Retenus par origine</div>
            <div class="donut-zone">
              <div class="donut" :style="donutStyle(segOrigine)">
                <div class="donut-hole"><span class="donut-val">{{ totalRetenus }}</span><span class="donut-lib">retenus</span></div>
              </div>
              <div class="legende">
                <div v-for="s in segOrigine" :key="s.label" class="legende-l">
                  <span class="pastille" :style="{ background: s.color }" />
                  <span class="flex-grow-1">{{ s.label }}</span>
                  <strong>{{ s.value }}</strong>
                  <span class="text-medium-emphasis ml-1">({{ pct(s.value, totalRetenus) }}%)</span>
                </div>
                <div v-if="!segOrigine.length" class="text-medium-emphasis text-caption">Aucun retenu.</div>
              </div>
            </div>
          </v-card>
        </v-col>
        <v-col cols="12" md="3">
          <v-card flat border class="pa-5 h-100">
            <div class="carte-titre">Recours par statut</div>
            <div class="donut-zone">
              <div class="donut" :style="donutStyle(segRecours)">
                <div class="donut-hole"><span class="donut-val">{{ totalRecours }}</span><span class="donut-lib">recours</span></div>
              </div>
              <div class="legende">
                <div v-for="s in segRecours" :key="s.key" class="legende-l">
                  <span class="pastille" :style="{ background: s.color }" />
                  <span class="flex-grow-1">{{ s.label }}</span>
                  <strong>{{ s.value }}</strong>
                  <span class="text-medium-emphasis ml-1">({{ pct(s.value, totalRecours) }}%)</span>
                </div>
                <div v-if="!segRecours.length" class="text-medium-emphasis text-caption">Aucun recours.</div>
              </div>
            </div>
          </v-card>
        </v-col>
      </v-row>

      <!-- Niveau de traitement -->
      <v-card flat border class="pa-5 mb-2">
        <div class="carte-titre mb-3">Niveau de traitement</div>
        <v-row dense>
          <v-col cols="12" md="4">
            <div class="jauge-bloc">
              <div class="jauge-tete">
                <span><v-icon size="18" color="#EF6C00" class="mr-1">mdi-folder-multiple</v-icon>Dossiers</span>
                <strong class="jauge-pct">{{ pct(trDossiers.traite, trDossiers.total) }}%</strong>
              </div>
              <div class="jauge"><div class="jauge-fill" :style="{ width: pct(trDossiers.traite, trDossiers.total) + '%', background: '#2E7D32' }" /></div>
              <div class="jauge-sous">{{ trDossiers.traite }} traités · {{ trDossiers.en_attente }} à traiter</div>
            </div>
          </v-col>
          <v-col cols="12" md="4">
            <div class="jauge-bloc">
              <div class="jauge-tete">
                <span><v-icon size="18" color="#6A1B9A" class="mr-1">mdi-account-alert-outline</v-icon>Réclamations</span>
                <strong class="jauge-pct">{{ pct(trReclam.traite, trReclam.total) }}%</strong>
              </div>
              <div class="jauge"><div class="jauge-fill" :style="{ width: pct(trReclam.traite, trReclam.total) + '%', background: '#6A1B9A' }" /></div>
              <div class="jauge-sous">{{ trReclam.traite }} traitées · {{ trReclam.en_attente }} à traiter</div>
            </div>
          </v-col>
          <v-col cols="12" md="4">
            <div class="jauge-bloc">
              <div class="jauge-tete">
                <span><v-icon size="18" color="#5E35B1" class="mr-1">mdi-gavel</v-icon>Recours</span>
                <strong class="jauge-pct">{{ pct(trRecours.traite, trRecours.total) }}%</strong>
              </div>
              <div class="jauge"><div class="jauge-fill" :style="{ width: pct(trRecours.traite, trRecours.total) + '%', background: '#5E35B1' }" /></div>
              <div class="jauge-sous">{{ trRecours.traite }} traités · {{ trRecours.en_attente }} à traiter</div>
            </div>
          </v-col>
        </v-row>
      </v-card>

      <!-- Barres par poste -->
      <v-row dense>
        <v-col cols="12" md="6">
          <v-card flat border class="pa-5 h-100">
            <div class="carte-titre mb-3">Retenus par poste</div>
            <div v-for="(p, i) in retenusPoste" :key="p.poste" class="barre-l">
              <span class="barre-lbl">{{ p.poste }}</span>
              <span class="barre-piste">
                <span class="barre-fill" :style="{ width: (p.n / maxRetenusPoste * 100) + '%', background: COULEURS_POSTE[i % COULEURS_POSTE.length] }" />
              </span>
              <span class="barre-val">{{ p.n }}</span>
            </div>
            <div v-if="!retenusPoste.length" class="text-medium-emphasis text-caption">Aucun retenu.</div>
          </v-card>
        </v-col>
        <v-col cols="12" md="6">
          <v-card flat border class="pa-5 h-100">
            <div class="carte-titre mb-3">Dossiers reçus par poste</div>
            <div v-for="p in dossiersPoste" :key="p.poste" class="barre-l barre-l2">
              <span class="barre-lbl">{{ p.poste }}</span>
              <span class="barre-piste">
                <span class="barre-fill" :style="{ width: (p.recus / maxRecusPoste * 100) + '%', background: '#0288D1' }" />
                <span class="barre-fill-sur" :style="{ width: (p.retenus / maxRecusPoste * 100) + '%' }" :title="p.retenus + ' retenu(s)'" />
              </span>
              <span class="barre-val">{{ p.recus }}<span class="text-success"> · {{ p.retenus }}✓</span></span>
            </div>
            <div v-if="!dossiersPoste.length" class="text-medium-emphasis text-caption">Aucun dossier reçu.</div>
          </v-card>
        </v-col>
      </v-row>
    </template>

    <v-card v-else-if="!chargement" flat border class="pa-10 text-center">
      <v-icon size="48" color="grey-lighten-1" class="mb-2">mdi-chart-box-outline</v-icon>
      <p class="text-body-2 text-medium-emphasis mb-0">Sélectionnez un appel à candidature pour afficher les rapports.</p>
    </v-card>
  </div>
</template>

<style scoped>
.h-100 { height: 100%; }
.carte-titre { font-size: 1rem; font-weight: 800; color: #1a237e; }
.donut-zone { display: flex; align-items: center; gap: 18px; flex-wrap: wrap; margin-top: 10px; }
.donut { width: 140px; height: 140px; border-radius: 50%; flex-shrink: 0; position: relative; }
.donut-hole { position: absolute; inset: 26px; background: #fff; border-radius: 50%; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.donut-val { font-size: 1.6rem; font-weight: 800; color: #1f2430; line-height: 1; }
.donut-lib { font-size: 0.66rem; text-transform: uppercase; letter-spacing: 0.04em; color: #9098a8; }
.legende { flex: 1; min-width: 150px; }
.legende-l { display: flex; align-items: center; gap: 8px; font-size: 0.85rem; padding: 3px 0; }
.pastille { width: 12px; height: 12px; border-radius: 3px; flex-shrink: 0; }
.jauge-bloc { padding: 6px 4px; }
.jauge-tete { display: flex; justify-content: space-between; align-items: center; font-weight: 700; color: #2c3344; font-size: 0.9rem; }
.jauge-pct { font-size: 1.2rem; color: #1a237e; }
.jauge { height: 16px; background: #eef0f5; border-radius: 9px; overflow: hidden; margin: 6px 0; }
.jauge-fill { height: 100%; border-radius: 9px; transition: width 0.6s cubic-bezier(0.22,1,0.36,1); }
.jauge-sous { font-size: 0.78rem; color: #8a92a4; }
.barre-l { display: grid; grid-template-columns: 150px 1fr 64px; align-items: center; gap: 10px; padding: 5px 0; }
.barre-lbl { font-size: 0.82rem; font-weight: 600; color: #2c3344; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.barre-piste { height: 16px; background: #f1f3f8; border-radius: 9px; overflow: hidden; position: relative; }
.barre-fill { display: block; height: 100%; min-width: 2px; border-radius: 9px; transition: width 0.55s; }
.barre-fill-sur { position: absolute; top: 0; left: 0; height: 100%; background: #2E7D32; border-radius: 9px; opacity: 0.95; }
.barre-val { font-size: 0.85rem; font-weight: 800; color: #1f2430; text-align: right; }
@media (max-width: 600px) { .barre-l { grid-template-columns: 110px 1fr 56px; } }
</style>
