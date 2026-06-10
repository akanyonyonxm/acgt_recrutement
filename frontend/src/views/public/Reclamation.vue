<script setup>
import { ref, onMounted } from 'vue'
import api, { initCsrf } from '../../api'

const appels = ref([])
const form = ref({ appel: null, nom: '', postnom: '', prenom: '', email: '', telephone: '', message: '' })
const docs = ref({ accuse: null, cv: null, identite: null })
const diplomes = ref([])
const siteWeb = ref('')        // honeypot anti-spam (doit rester vide)
const enCours = ref(false)
const envoye = ref(false)
const erreur = ref('')

// v-file-input peut renvoyer un File ou un tableau selon la version : on normalise.
const f = (v) => (Array.isArray(v) ? v[0] : v) || null
const arr = (v) => (Array.isArray(v) ? v : v ? [v] : [])

const valide = () =>
  form.value.appel && form.value.nom.trim() && form.value.prenom.trim() &&
  form.value.email.trim() && f(docs.value.accuse) && f(docs.value.cv) &&
  f(docs.value.identite) && arr(diplomes.value).length

onMounted(async () => {
  await initCsrf()
  const { data } = await api.get('/appels/')
  appels.value = data.results.filter((a) => a.statut === 'publie').map((a) => ({ value: a.id, title: a.titre }))
  if (appels.value.length === 1) form.value.appel = appels.value[0].value
})

async function envoyer() {
  erreur.value = ''
  if (!valide()) { erreur.value = 'Veuillez remplir les champs requis et joindre tous les justificatifs.'; return }
  enCours.value = true
  try {
    const fd = new FormData()
    Object.entries(form.value).forEach(([k, v]) => fd.append(k, v ?? ''))
    fd.append('accuse', f(docs.value.accuse))
    fd.append('cv', f(docs.value.cv))
    fd.append('identite', f(docs.value.identite))
    arr(diplomes.value).forEach((d) => fd.append('diplomes', d))
    fd.append('site_web', siteWeb.value)
    await api.post('/reclamations/', fd)
    envoye.value = true
  } catch (e) {
    erreur.value = e.response?.data?.detail || "Envoi impossible. Réessayez."
  } finally {
    enCours.value = false
  }
}
</script>

<template>
  <div>
    <section class="hero">
      <div class="hero-inner">
        <h1 class="hero-titre">Faire une réclamation</h1>
        <p class="hero-sous">
          Vous avez déposé un dossier à l'ACGT mais votre nom n'apparaît pas dans la liste ?
          Soumettez une réclamation en joignant votre <strong>accusé de réception</strong>,
          votre <strong>CV</strong>, la copie de votre <strong>pièce d'identité</strong> et
          la copie de vos <strong>diplômes</strong> (ou équivalent).
        </p>
      </div>
    </section>

    <div class="wrap">
      <v-card flat border rounded="lg" class="carte pa-6 pa-md-8">
        <div v-if="envoye" class="text-center py-6">
          <v-icon color="success" size="64" class="mb-3">mdi-check-circle</v-icon>
          <h2 class="text-h5 font-weight-bold text-primary mb-2">Réclamation envoyée</h2>
          <p class="text-body-1 text-medium-emphasis mb-6">
            Votre réclamation a bien été enregistrée. Vous recevrez une réponse par email.
          </p>
          <v-btn color="primary" variant="flat" :to="{ name: 'eligibles' }" prepend-icon="mdi-arrow-left">
            Retour à la liste
          </v-btn>
        </div>

        <template v-else>
          <div class="text-subtitle-1 font-weight-bold text-primary mb-3">Vos informations</div>
          <v-select v-model="form.appel" :items="appels" label="Appel à candidature concerné *"
                    prepend-inner-icon="mdi-bullhorn-outline" />
          <v-row dense>
            <v-col cols="12" sm="4"><v-text-field v-model="form.nom" label="Nom *" /></v-col>
            <v-col cols="12" sm="4"><v-text-field v-model="form.postnom" label="Post-nom" /></v-col>
            <v-col cols="12" sm="4"><v-text-field v-model="form.prenom" label="Prénom *" /></v-col>
          </v-row>
          <v-row dense>
            <v-col cols="12" sm="6">
              <v-text-field v-model="form.email" label="Email de contact *" type="email"
                            prepend-inner-icon="mdi-email-outline" />
            </v-col>
            <v-col cols="12" sm="6">
              <v-text-field v-model="form.telephone" label="Téléphone" prepend-inner-icon="mdi-phone-outline" />
            </v-col>
          </v-row>

          <v-divider class="my-4" />
          <div class="text-subtitle-1 font-weight-bold text-primary mb-1">Pièces justificatives</div>
          <p class="text-caption text-medium-emphasis mb-3">PDF, image ou Word — 5 Mo max par fichier.</p>

          <v-file-input v-model="docs.accuse" label="Accusé de réception (ACGT) *"
                        prepend-icon="" prepend-inner-icon="mdi-file-certificate-outline"
                        accept=".pdf,.jpg,.jpeg,.png,.doc,.docx" show-size />
          <v-file-input v-model="docs.cv" label="CV *"
                        prepend-icon="" prepend-inner-icon="mdi-file-account-outline"
                        accept=".pdf,.jpg,.jpeg,.png,.doc,.docx" show-size />
          <v-file-input v-model="docs.identite" label="Copie de la pièce d'identité *"
                        prepend-icon="" prepend-inner-icon="mdi-card-account-details-outline"
                        accept=".pdf,.jpg,.jpeg,.png,.doc,.docx" show-size />
          <v-file-input v-model="diplomes" label="Copie des diplômes (un ou plusieurs) *"
                        prepend-icon="" prepend-inner-icon="mdi-school-outline" multiple counter
                        accept=".pdf,.jpg,.jpeg,.png,.doc,.docx" show-size />

          <v-textarea v-model="form.message" label="Message (facultatif)" rows="3" class="mt-2" />

          <input v-model="siteWeb" type="text" name="site_web" tabindex="-1" autocomplete="off"
                 class="hp" aria-hidden="true" />

          <v-alert v-if="erreur" type="error" variant="tonal" density="compact" class="mt-2">{{ erreur }}</v-alert>

          <div class="d-flex align-center flex-wrap ga-3 mt-4">
            <span class="text-caption text-medium-emphasis">* champs obligatoires</span>
            <v-spacer />
            <v-btn variant="text" :to="{ name: 'eligibles' }">Annuler</v-btn>
            <v-btn color="accent" size="large" rounded="lg" class="text-primary font-weight-bold"
                   prepend-icon="mdi-send" :loading="enCours" :disabled="!valide()" @click="envoyer">
              Envoyer la réclamation
            </v-btn>
          </div>
        </template>
      </v-card>
    </div>
  </div>
</template>

<style scoped>
.hero { background: linear-gradient(135deg, #1a237e 0%, #0d1b2a 100%); padding: 48px 24px 56px; }
.hero-inner { max-width: 760px; margin: 0 auto; text-align: center; }
.hero-titre { color: #fff; font-size: clamp(2rem, 5vw, 3rem); font-weight: 800; letter-spacing: -0.5px; }
.hero-sous { color: #fff; opacity: 0.9; font-size: 1.02rem; line-height: 1.6; max-width: 640px; margin: 14px auto 0; }
.wrap { max-width: 820px; margin: 0 auto; padding: 0 24px 56px; }
.carte { margin-top: -32px; position: relative; z-index: 2; box-shadow: 0 12px 30px rgba(26,35,126,0.10); }
.hp { position: absolute; left: -9999px; width: 1px; height: 1px; opacity: 0; }
</style>
