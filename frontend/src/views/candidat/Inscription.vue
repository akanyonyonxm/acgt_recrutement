<script setup>
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import api from '../../api'
import logo from '../../assets/acgt_logo.png'

const email = ref('')
const motDePasse = ref('')
const show = ref(false)
const erreur = ref('')
const enCours = ref(false)
const fait = ref(false)

async function soumettre() {
  erreur.value = ''
  enCours.value = true
  try {
    await api.post('/auth/inscription/', {
      email: email.value, mot_de_passe: motDePasse.value,
    })
    fait.value = true
  } catch (e) {
    const d = e.response?.data
    erreur.value = d?.email?.[0] || d?.mot_de_passe?.[0] || d?.detail || 'Inscription impossible.'
  } finally {
    enCours.value = false
  }
}
</script>

<template>
  <div class="mesh">
    <v-container class="py-10 d-flex justify-center">
    <v-card class="pa-2 glass" max-width="460" width="100%">
      <div class="text-center pt-6 px-6">
        <div class="logo-box mb-3"><img :src="logo" alt="ACGT" width="64" /></div>
        <h1 class="text-h6 font-weight-bold" style="color:#00838F">Créer un compte candidat</h1>
        <p class="text-body-2 text-medium-emphasis">Rejoignez la plateforme de recrutement ACGT</p>
      </div>

      <v-card-text class="px-6 pb-6">
        <v-alert v-if="fait" type="success" variant="tonal" icon="mdi-email-check">
          Compte créé. Un email d'activation vient d'être envoyé à
          <strong>{{ email }}</strong>. Cliquez sur le lien reçu pour activer votre compte,
          puis connectez-vous.
          <div class="mt-3">
            <v-btn color="primary" variant="flat" size="small" :to="{ name: 'candidat-connexion' }">
              Aller à la connexion
            </v-btn>
          </div>
        </v-alert>

        <v-form v-else @submit.prevent="soumettre">
          <v-text-field v-model="email" label="Email" type="email" prepend-inner-icon="mdi-email"
                        :rules="[(v) => !!v || 'Requis']" class="mb-2" />
          <v-text-field v-model="motDePasse" label="Mot de passe"
                        :type="show ? 'text' : 'password'" prepend-inner-icon="mdi-lock"
                        :append-inner-icon="show ? 'mdi-eye-off' : 'mdi-eye'"
                        @click:append-inner="show = !show"
                        hint="8 caractères minimum" persistent-hint class="mb-3" />
          <v-alert v-if="erreur" type="error" variant="tonal" density="compact" class="mb-3">{{ erreur }}</v-alert>
          <v-btn type="submit" color="accent" block size="large" rounded="lg"
                 class="text-primary font-weight-bold" :loading="enCours" prepend-icon="mdi-account-plus">
            Créer mon compte
          </v-btn>
        </v-form>

        <div class="text-center mt-4 text-body-2">
          Déjà inscrit ?
          <RouterLink :to="{ name: 'candidat-connexion' }">Se connecter</RouterLink>
        </div>
      </v-card-text>
    </v-card>
    </v-container>
  </div>
</template>

<style scoped>
.mesh {
  min-height: 100vh;
  background-color: #0d1b2a;
  background-image:
    radial-gradient(at 0% 0%, hsla(234, 70%, 25%, 1) 0, transparent 50%),
    radial-gradient(at 80% 0%, hsla(242, 57%, 35%, 1) 0, transparent 50%),
    radial-gradient(at 100% 100%, hsla(220, 80%, 20%, 1) 0, transparent 50%);
  display: flex; align-items: center;
}
.glass {
  background: rgba(255, 255, 255, 0.97) !important;
  backdrop-filter: blur(10px);
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.45) !important;
}
.logo-box {
  width: 88px; height: 88px; margin: 0 auto;
  background: #fff; border: 4px solid #f5f5f5; border-radius: 20px;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}
</style>
