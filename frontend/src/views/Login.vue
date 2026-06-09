<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import logo from '../assets/acgt_logo.png'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const email = ref('')
const motDePasse = ref('')
const showPassword = ref(false)
const erreur = ref('')
const enCours = ref(false)

async function soumettre() {
  erreur.value = ''
  enCours.value = true
  try {
    await auth.connexion(email.value, motDePasse.value)
    if (route.query.suite) {
      router.push(route.query.suite)
    } else if (auth.estAdmin) {
      router.push({ name: 'validation' })
    } else if (auth.estEvaluateur) {
      router.push({ name: 'eval-dossiers' })
    } else {
      erreur.value = "Ce compte n'a pas accès à l'espace de traitement."
      await auth.deconnexion()
    }
  } catch (e) {
    erreur.value = e.response?.data?.detail || 'Email ou mot de passe incorrect.'
  } finally {
    enCours.value = false
  }
}
</script>

<template>
  <v-main class="login-bg">
    <div class="bg-overlay"></div>
    <v-container fluid class="fill-height pa-0">
      <v-row align="center" justify="center" class="fill-height ma-0">
        <v-col cols="12" sm="8" md="5" lg="4">
          <v-card class="login-card rounded-xl elevation-24" :loading="enCours">
            <div class="text-center pt-10 px-6">
              <img :src="logo" alt="ACGT" width="160" class="mb-4" />
              <h1 class="text-h5 font-weight-bold text-primary mb-2">
                Traitement des candidatures
              </h1>
              <div class="text-subtitle-2 text-medium-emphasis mb-2">
                Espace de traitement — connectez-vous pour continuer
              </div>
            </div>

            <v-card-text class="px-8 pb-10">
              <v-form @submit.prevent="soumettre">
                <div class="text-caption font-weight-bold text-uppercase text-medium-emphasis mb-1 ml-1">Email</div>
                <v-text-field
                  v-model="email"
                  type="email"
                  placeholder="vous@acgt.cd"
                  prepend-inner-icon="mdi-account-outline"
                  bg-color="grey-lighten-5"
                  rounded="lg"
                  autofocus
                  class="mb-3"
                />
                <div class="text-caption font-weight-bold text-uppercase text-medium-emphasis mb-1 ml-1">Mot de passe</div>
                <v-text-field
                  v-model="motDePasse"
                  :type="showPassword ? 'text' : 'password'"
                  prepend-inner-icon="mdi-lock-outline"
                  :append-inner-icon="showPassword ? 'mdi-eye-outline' : 'mdi-eye-off-outline'"
                  @click:append-inner="showPassword = !showPassword"
                  bg-color="grey-lighten-5"
                  rounded="lg"
                  class="mb-4"
                />
                <v-scale-transition>
                  <v-alert
                    v-if="erreur"
                    type="error"
                    variant="tonal"
                    icon="mdi-alert-circle"
                    border="start"
                    density="comfortable"
                    class="mb-4 rounded-lg"
                  >{{ erreur }}</v-alert>
                </v-scale-transition>
                <v-btn
                  type="submit"
                  color="primary"
                  size="large"
                  block
                  rounded="lg"
                  :loading="enCours"
                  prepend-icon="mdi-login"
                >Se connecter</v-btn>
              </v-form>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-container>
  </v-main>
</template>

<style scoped>
.login-bg {
  background: radial-gradient(circle at center, #1a237e 0%, #0d1b2a 100%);
  position: relative;
  overflow: hidden;
}
.bg-overlay {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
  background-size: 40px 40px;
  pointer-events: none;
}
.login-card {
  background-color: rgba(255, 255, 255, 0.97) !important;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5) !important;
}
</style>
