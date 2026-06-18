<script setup>
import { ref, computed } from 'vue'
import api, { initCsrf } from '../../api'

// Étape 1 : rechercher son identité. Étape 2 : déposer le recours.
const q = ref('')
const resultats = ref(null)     // { dossiers: [], reclamations: [] }
const enRecherche = ref(false)
const erreurRech = ref('')

const selection = ref(null)     // { nom, postnom, prenom } choisi
const form = ref({ date_naissance: '', email: '', message: '' })
const enCours = ref(false)
const envoye = ref(false)
const erreur = ref('')

const nbResultats = computed(() =>
  resultats.value ? resultats.value.dossiers.length + resultats.value.reclamations.length : 0)
const valide = () => selection.value && form.value.date_naissance && form.value.email.trim() && form.value.message.trim()

async function rechercher() {
  erreurRech.value = ''
  resultats.value = null
  selection.value = null
  if (!q.value.trim()) { erreurRech.value = 'Veuillez saisir votre nom (et prénom).'; return }
  enRecherche.value = true
  try {
    await initCsrf()
    const { data } = await api.get('/recours/rechercher/', { params: { q: q.value.trim() } })
    resultats.value = data
  } catch {
    erreurRech.value = 'Recherche impossible. Réessayez.'
  } finally {
    enRecherche.value = false
  }
}

function choisir(p) {
  selection.value = { ...p }   // { type, id, nom, postnom, prenom, poste, appel }
  erreur.value = ''
  // Remonter vers le formulaire après sélection.
  setTimeout(() => document.getElementById('form-recours')?.scrollIntoView({ behavior: 'smooth' }), 50)
}

async function envoyer() {
  erreur.value = ''
  if (!form.value.date_naissance) { erreur.value = 'Veuillez indiquer votre date de naissance.'; return }
  if (!form.value.email.trim()) { erreur.value = 'Veuillez indiquer votre email.'; return }
  if (!form.value.message.trim()) { erreur.value = 'Veuillez saisir votre message.'; return }
  enCours.value = true
  try {
    await api.post('/recours/', {
      source_type: selection.value.type,
      source_id: selection.value.id,
      date_naissance: form.value.date_naissance,
      email: form.value.email.trim(),
      message: form.value.message.trim(),
    })
    envoye.value = true
  } catch (e) {
    erreur.value = e.response?.data?.detail
      || e.response?.data?.date_naissance?.[0]
      || e.response?.data?.email?.[0]
      || e.response?.data?.source_id?.[0]
      || 'Envoi impossible. Réessayez.'
  } finally {
    enCours.value = false
  }
}

const nomComplet = (p) => [p.nom, p.postnom, p.prenom].filter(Boolean).join(' ')
</script>

<template>
  <div>
    <section class="hero">
      <div class="hero-inner">
        <h1 class="hero-titre">Déposer un recours</h1>
        <p class="hero-sous">
          Recherchez d'abord votre <strong>nom</strong> pour confirmer que vous figurez bien
          dans notre base (réclamations et dossiers déposés), puis transmettez votre recours.
        </p>
      </div>
    </section>

    <div class="wrap">
      <v-card flat border rounded="lg" class="carte pa-6 pa-md-8">
        <div v-if="envoye" class="text-center py-6">
          <v-icon color="success" size="64" class="mb-3">mdi-check-circle</v-icon>
          <h2 class="text-h5 font-weight-bold text-primary mb-2">Recours envoyé</h2>
          <p class="text-body-1 text-medium-emphasis mb-6">
            Votre recours a bien été enregistré. Il sera examiné par nos services.
          </p>
          <v-btn color="primary" variant="flat" :to="{ name: 'retenus-public' }" prepend-icon="mdi-arrow-left">
            Retour à la liste des retenus
          </v-btn>
        </div>

        <template v-else>
          <!-- Étape 1 : recherche -->
          <div class="text-subtitle-1 font-weight-bold text-primary mb-3">1. Retrouvez votre nom</div>
          <div class="d-flex align-start ga-3 flex-wrap">
            <v-text-field v-model="q" label="Nom, postnom, prénom *" prepend-inner-icon="mdi-account-search"
                          style="min-width: 260px; flex: 1" @keyup.enter="rechercher" clearable />
            <v-btn color="primary" variant="flat" size="large" class="mt-1"
                   :loading="enRecherche" prepend-icon="mdi-magnify" @click="rechercher">
              Rechercher
            </v-btn>
          </div>
          <v-alert v-if="erreurRech" type="error" variant="tonal" density="compact" class="mt-1">{{ erreurRech }}</v-alert>

          <!-- Résultats distincts -->
          <template v-if="resultats">
            <v-alert v-if="nbResultats === 0" type="warning" variant="tonal" density="comfortable" class="mt-3">
              Aucune correspondance trouvée. Vérifiez l'orthographe de votre nom.
            </v-alert>

            <div v-else class="mt-4">
              <p class="text-body-2 text-medium-emphasis mb-3">
                Cliquez sur la ligne qui vous correspond pour continuer.
              </p>
              <v-row dense>
                <v-col cols="12" md="6">
                  <div class="bloc-titre"><v-icon size="18" color="#00838F">mdi-account-alert-outline</v-icon>
                    Réclamations <span class="cpt">{{ resultats.reclamations.length }}</span></div>
                  <div v-if="!resultats.reclamations.length" class="vide-bloc">Aucune</div>
                  <button v-for="(p, i) in resultats.reclamations" :key="'r' + i" class="ligne"
                          :class="{ sel: selection && selection.type === p.type && selection.id === p.id }" @click="choisir(p)">
                    <span class="ln-nom">{{ nomComplet(p) }}</span>
                    <span class="ln-meta">{{ [p.poste, p.appel].filter(Boolean).join(' · ') }}</span>
                  </button>
                </v-col>
                <v-col cols="12" md="6">
                  <div class="bloc-titre"><v-icon size="18" color="#1a237e">mdi-folder-account-outline</v-icon>
                    Dossiers déposés <span class="cpt">{{ resultats.dossiers.length }}</span></div>
                  <div v-if="!resultats.dossiers.length" class="vide-bloc">Aucun</div>
                  <button v-for="(p, i) in resultats.dossiers" :key="'d' + i" class="ligne"
                          :class="{ sel: selection && selection.type === p.type && selection.id === p.id }" @click="choisir(p)">
                    <span class="ln-nom">{{ nomComplet(p) }}</span>
                    <span class="ln-meta">{{ [p.poste, p.appel].filter(Boolean).join(' · ') }}</span>
                  </button>
                </v-col>
              </v-row>
            </div>
          </template>

          <!-- Étape 2 : formulaire (après sélection) -->
          <template v-if="selection">
            <v-divider class="my-5" />
            <div id="form-recours" class="text-subtitle-1 font-weight-bold text-primary mb-1">2. Votre recours</div>
            <v-alert type="success" variant="tonal" density="comfortable" class="mb-4" icon="mdi-account-check">
              <span class="font-weight-bold">{{ nomComplet(selection) }}</span>
            </v-alert>
            <v-text-field v-model="form.date_naissance" label="Date de naissance *" type="date"
                          prepend-inner-icon="mdi-cake-variant-outline"
                          hint="Doit correspondre à votre pièce d'identité (vérification)." persistent-hint
                          class="mb-2" />
            <v-text-field v-model="form.email" label="Adresse email *" type="email"
                          prepend-inner-icon="mdi-email-outline" />
            <v-textarea v-model="form.message" label="Message à transmettre *" rows="4"
                        hint="Expliquez l'objet de votre recours." persistent-hint />

            <v-alert v-if="erreur" type="error" variant="tonal" density="compact" class="mt-2">{{ erreur }}</v-alert>

            <div class="d-flex align-center flex-wrap ga-3 mt-4">
              <span class="text-caption text-medium-emphasis">* champs obligatoires</span>
              <v-spacer />
              <v-btn variant="text" :to="{ name: 'retenus-public' }">Annuler</v-btn>
              <v-btn color="accent" size="large" rounded="lg" class="text-primary font-weight-bold"
                     prepend-icon="mdi-send" :loading="enCours" :disabled="!valide()" @click="envoyer">
                Envoyer le recours
              </v-btn>
            </div>
          </template>
        </template>
      </v-card>
    </div>
  </div>
</template>

<style scoped>
.hero { background: linear-gradient(135deg, #1a237e 0%, #0d1b2a 100%); padding: 48px 24px 56px; }
.hero-inner { max-width: 760px; margin: 0 auto; text-align: center; }
.hero-titre { color: #fff; font-size: clamp(2rem, 5vw, 3rem); font-weight: 800; letter-spacing: -0.5px; }
.hero-sous { color: #fff; opacity: 0.9; font-size: 1.02rem; line-height: 1.6; max-width: 680px; margin: 14px auto 0; }
.wrap { max-width: 820px; margin: 0 auto; padding: 0 24px 56px; }
.carte { margin-top: -32px; position: relative; z-index: 2; box-shadow: 0 12px 30px rgba(26,35,126,0.10); }
.bloc-titre { display: flex; align-items: center; gap: 6px; font-weight: 700; color: #1f2933; font-size: 0.9rem; margin-bottom: 8px; }
.cpt { background: #eae7ef; color: #1a237e; border-radius: 9999px; padding: 1px 9px; font-size: 0.78rem; }
.vide-bloc { color: #9aa0ab; font-size: 0.85rem; padding: 8px 4px; }
.ligne { display: flex; flex-direction: column; align-items: flex-start; width: 100%; text-align: left;
  border: 1px solid #d8dbe6; border-radius: 12px; padding: 10px 14px; margin-bottom: 8px; background: #fff;
  cursor: pointer; transition: border-color 0.15s, background 0.15s; }
.ligne:hover { border-color: #1a237e; background: #f5f6fb; }
.ligne.sel { border-color: #2E7D32; background: #e9f6ec; box-shadow: 0 0 0 1px #2E7D32; }
.ln-nom { font-weight: 700; color: #1b1b21; }
.ln-meta { font-size: 0.8rem; color: #66707e; }
</style>
