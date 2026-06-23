<script setup>
import { ref } from 'vue'
import api, { initCsrf } from '../../api'

// Étape 1 : saisir son CODE (et voir son nom). Étape 2 : préciser la ville.
const code = ref('')
const resultats = ref(null)        // tableau d'entrées définitives (0 ou 1 par code)
const enRecherche = ref(false)
const erreurRech = ref('')

const selection = ref(null)        // entrée trouvée
const form = ref({ date_naissance: '', ville: '' })
const enCours = ref(false)
const envoye = ref(false)
const erreur = ref('')

// Choix réservé aux candidats hors Kinshasa : Lubumbashi ou Mbuji-Mayi.
// (Kinshasa reste la valeur par défaut pour ceux qui ne précisent rien.)
const VILLES = [
  { value: 'lubumbashi', label: 'Lubumbashi' },
  { value: 'mbuji_mayi', label: 'Mbuji-Mayi' },
]
const aff = (v) => (v || '').normalize('NFKC')
const nomComplet = (e) => [aff(e.nom), aff(e.postnom), aff(e.prenom)].filter(Boolean).join(' ')
const valide = () => selection.value && form.value.date_naissance && form.value.ville

async function rechercher() {
  erreurRech.value = ''; resultats.value = null; selection.value = null; envoye.value = false
  if (!code.value.trim()) { erreurRech.value = 'Veuillez saisir votre code (ex. 0001).'; return }
  enRecherche.value = true
  try {
    await initCsrf()
    const { data } = await api.get('/retenus-definitifs/', { params: { code: code.value.trim() } })
    resultats.value = data.results
    if (data.results.length === 1) choisir(data.results[0])
  } catch {
    erreurRech.value = 'Recherche impossible. Réessayez.'
  } finally {
    enRecherche.value = false
  }
}

function choisir(e) {
  selection.value = { ...e }
  // Pré-coche la ville déjà choisie si ce n'est pas Kinshasa ; sinon laisse vide.
  form.value.ville = (e.ville_examen && e.ville_examen !== 'kinshasa') ? e.ville_examen : ''
  erreur.value = ''
  setTimeout(() => document.getElementById('form-ville')?.scrollIntoView({ behavior: 'smooth' }), 50)
}

async function envoyer() {
  erreur.value = ''
  if (!form.value.date_naissance) { erreur.value = 'Veuillez indiquer votre date de naissance.'; return }
  if (!form.value.ville) { erreur.value = 'Veuillez choisir une ville.'; return }
  enCours.value = true
  try {
    await api.post('/retenus-definitifs/choisir-ville/', {
      id: selection.value.id,
      date_naissance: form.value.date_naissance,
      ville: form.value.ville,
    })
    envoye.value = true
  } catch (e) {
    erreur.value = e.response?.data?.ville?.[0]
      || e.response?.data?.date_naissance?.[0]
      || e.response?.data?.detail
      || 'Envoi impossible. Réessayez.'
  } finally {
    enCours.value = false
  }
}
const libelleVille = (v) => (VILLES.find((x) => x.value === v) || {}).label || v
</script>

<template>
  <div>
    <section class="hero">
      <div class="hero-inner">
        <h1 class="hero-titre">Ville d'examen</h1>
        <p class="hero-sous">
          Vous passez le test <strong>en dehors de Kinshasa</strong> ? Saisissez votre <strong>code</strong>,
          vérifiez votre nom, puis choisissez <strong>Lubumbashi</strong> ou <strong>Mbuji-Mayi</strong>.
        </p>
        <RouterLink :to="{ name: 'retenus-public' }" class="hero-lien">
          Voir la liste des candidats admis
        </RouterLink>
      </div>
    </section>

    <div class="wrap">
      <v-card flat border rounded="lg" class="carte pa-6 pa-md-8">
        <div v-if="envoye" class="text-center py-6">
          <v-icon color="success" size="64" class="mb-3">mdi-clock-check-outline</v-icon>
          <h2 class="text-h5 font-weight-bold text-primary mb-2">Demande enregistrée</h2>
          <p class="text-body-1 text-medium-emphasis mb-6">
            Votre demande pour <strong>{{ libelleVille(form.ville) }}</strong> a bien été reçue.
            Elle sera <strong>validée par nos services</strong> ; sans validation, le test reste à Kinshasa.
          </p>
          <v-btn color="primary" variant="flat" :to="{ name: 'retenus-public' }" prepend-icon="mdi-arrow-left">
            Retour à la liste des retenus
          </v-btn>
        </div>

        <template v-else>
          <!-- Étape 1 : code -->
          <div class="text-subtitle-1 font-weight-bold text-primary mb-3">1. Saisissez votre code</div>
          <div class="d-flex align-start ga-3 flex-wrap">
            <v-text-field v-model="code" label="Votre code (ex. 0001) *" prepend-inner-icon="mdi-pound"
                          hint="Le code figure sur la liste des candidats admis." persistent-hint
                          style="min-width: 260px; flex: 1" @keyup.enter="rechercher" clearable />
            <v-btn color="primary" variant="flat" size="large" class="mt-1"
                   :loading="enRecherche" prepend-icon="mdi-magnify" @click="rechercher">Rechercher</v-btn>
          </div>
          <v-alert v-if="erreurRech" type="error" variant="tonal" density="compact" class="mt-1">{{ erreurRech }}</v-alert>

          <v-alert v-if="resultats && !resultats.length" type="warning" variant="tonal" density="comfortable" class="mt-3">
            Aucun candidat avec ce code dans la liste définitive. Vérifiez votre code sur la liste des candidats admis.
          </v-alert>

          <!-- Étape 2 : ville -->
          <template v-if="selection">
            <v-divider class="my-5" />
            <div id="form-ville" class="text-subtitle-1 font-weight-bold text-primary mb-1">2. Votre ville d'examen</div>
            <v-alert type="success" variant="tonal" density="comfortable" class="mb-4" icon="mdi-account-check">
              <span class="font-weight-bold">{{ selection.code }} — {{ nomComplet(selection) }}</span>
            </v-alert>
            <v-text-field v-model="form.date_naissance" label="Date de naissance *" type="date"
                          prepend-inner-icon="mdi-cake-variant-outline"
                          hint="Pour confirmer votre identité." persistent-hint class="mb-3" />
            <div class="text-caption text-medium-emphasis mb-2">
              Ville (hors Kinshasa) où vous passerez le test * — sans choix, le test reste à Kinshasa.
            </div>
            <div class="villes">
              <button v-for="v in VILLES" :key="v.value" type="button" class="ville-opt"
                      :class="{ sel: form.ville === v.value }" @click="form.ville = v.value">
                <v-icon :color="form.ville === v.value ? 'success' : 'grey'" size="26">mdi-map-marker</v-icon>
                <span class="ville-nom">{{ v.label }}</span>
                <v-icon v-if="form.ville === v.value" color="success" size="20" class="ville-check">mdi-check-circle</v-icon>
              </button>
            </div>

            <v-alert v-if="erreur" type="error" variant="tonal" density="compact" class="mt-3">{{ erreur }}</v-alert>

            <div class="d-flex align-center flex-wrap ga-3 mt-4">
              <span class="text-caption text-medium-emphasis">* champs obligatoires</span>
              <v-spacer />
              <v-btn variant="text" :to="{ name: 'retenus-public' }">Annuler</v-btn>
              <v-btn color="success" size="large" rounded="lg" class="font-weight-bold"
                     prepend-icon="mdi-send" :loading="enCours" :disabled="!valide()" @click="envoyer">
                Envoyer ma demande
              </v-btn>
            </div>
          </template>
        </template>
      </v-card>
    </div>
  </div>
</template>

<style scoped>
.hero { background: linear-gradient(135deg, #1b5e20 0%, #0b3d1a 100%); padding: 48px 24px 56px; }
.hero-inner { max-width: 760px; margin: 0 auto; text-align: center; }
.hero-titre { color: #fff; font-size: clamp(2rem, 5vw, 3rem); font-weight: 800; letter-spacing: -0.5px; }
.hero-sous { color: #fff; opacity: 0.92; font-size: 1.02rem; line-height: 1.6; max-width: 680px; margin: 14px auto 0; }
.hero-sous strong { color: #FDD835; }
.hero-lien { display: inline-flex; align-items: center; gap: 6px; margin-top: 16px; color: #fff;
  font-weight: 700; text-decoration: underline; opacity: 0.95; }
.hero-lien:hover { opacity: 1; }
.fleche { font-size: 1.2rem; line-height: 1; }
.wrap { max-width: 820px; margin: 0 auto; padding: 0 24px 56px; }
.carte { margin-top: -32px; position: relative; z-index: 2; box-shadow: 0 12px 30px rgba(27,94,32,0.12); }
.ligne { display: grid; grid-template-columns: 70px 1fr auto; align-items: center; gap: 12px; width: 100%; text-align: left;
  border: 1px solid #d8dbe6; border-radius: 12px; padding: 10px 14px; margin-bottom: 8px; background: #fff;
  cursor: pointer; transition: border-color 0.15s, background 0.15s; }
.ligne:hover { border-color: #2E7D32; background: #f3faf4; }
.ligne.sel { border-color: #2E7D32; background: #e9f6ec; box-shadow: 0 0 0 1px #2E7D32; }
.ln-code { font-weight: 800; color: #1b5e20; }
.ln-nom { font-weight: 700; color: #1b1b21; text-transform: uppercase; }
.ln-meta { font-size: 0.8rem; color: #66707e; }
@media (max-width: 600px) { .ligne { grid-template-columns: 56px 1fr; } .ln-meta { grid-column: 2; } }

/* Choix de ville en cartes cliquables */
.villes { display: flex; gap: 14px; flex-wrap: wrap; }
.ville-opt { flex: 1; min-width: 150px; display: flex; align-items: center; gap: 10px; cursor: pointer;
  border: 1.5px solid #d8dbe6; border-radius: 14px; background: #fff; padding: 16px 18px; position: relative;
  font-size: 1.05rem; font-weight: 700; color: #1b1b21; transition: border-color 0.15s, background 0.15s, box-shadow 0.15s; }
.ville-opt:hover { border-color: #2E7D32; background: #f3faf4; }
.ville-opt.sel { border-color: #2E7D32; background: #e9f6ec; box-shadow: 0 0 0 1px #2E7D32; }
.ville-nom { flex: 1; }
.ville-check { position: absolute; top: 8px; right: 10px; }
</style>
