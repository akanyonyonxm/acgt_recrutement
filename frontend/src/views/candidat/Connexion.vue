<script setup>
import { ref } from 'vue'
import { RouterLink, useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import logo from '../../assets/acgt_logo.png'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const email = ref('')
const motDePasse = ref('')
const show = ref(false)
const erreur = ref('')
const enCours = ref(false)

async function soumettre() {
  erreur.value = ''
  enCours.value = true
  try {
    await auth.connexion(email.value, motDePasse.value)
    router.push(route.query.suite || { name: 'mes-dossiers' })
  } catch (e) {
    erreur.value = e.response?.data?.detail || 'Email ou mot de passe incorrect.'
  } finally {
    enCours.value = false
  }
}
</script>

<template>
  <div class="mesh">
    <RouterLink :to="{ name: 'eligibles' }" class="lien-accueil">
      <v-icon size="18" class="mr-1">mdi-arrow-left</v-icon>
      Retour à l'accueil
    </RouterLink>
    <v-container class="py-10 d-flex justify-center">
    <v-card class="pa-2 glass" max-width="440" width="100%">
      <div class="text-center pt-6 px-6">
        <RouterLink :to="{ name: 'eligibles' }" class="logo-box mb-3 d-inline-flex">
          <img :src="logo" alt="ACGT — Accueil" width="64" />
        </RouterLink>
        <h1 class="text-h6 font-weight-bold text-primary">Connexion candidat</h1>
        <p class="text-body-2 text-medium-emphasis">Accédez à votre espace sécurisé</p>
      </div>
      <v-card-text class="px-6 pb-6">
        <v-form @submit.prevent="soumettre">
          <v-text-field v-model="email" label="Email" type="email" prepend-inner-icon="mdi-email" class="mb-2" autofocus />
          <v-text-field v-model="motDePasse" label="Mot de passe"
                        :type="show ? 'text' : 'password'" prepend-inner-icon="mdi-lock"
                        :append-inner-icon="show ? 'mdi-eye-off' : 'mdi-eye'"
                        @click:append-inner="show = !show" class="mb-3" />
          <v-alert v-if="erreur" type="error" variant="tonal" density="compact" class="mb-3">{{ erreur }}</v-alert>
          <v-btn type="submit" color="accent" block size="large" rounded="lg"
                 class="text-primary font-weight-bold" :loading="enCours" append-icon="mdi-arrow-right">
            Se connecter
          </v-btn>
        </v-form>
        <div class="text-center mt-6 pt-4 text-body-2" style="border-top: 1px solid #e0e4e9">
          Pas encore de compte ?
          <RouterLink :to="{ name: 'candidat-inscription' }" class="font-weight-bold">Créer un compte</RouterLink>
        </div>
      </v-card-text>
    </v-card>
    </v-container>
  </div>
</template>

<style scoped>
.mesh {
  position: relative;
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
  transition: transform 0.2s, box-shadow 0.2s;
}
.logo-box:hover { transform: translateY(-2px); box-shadow: 0 8px 18px rgba(0,0,0,0.18); }

/* Lien de retour à l'accueil, posé en haut à gauche sur le fond sombre. */
.lien-accueil {
  position: absolute; top: 24px; left: 24px;
  display: inline-flex; align-items: center;
  color: rgba(255, 255, 255, 0.85); text-decoration: none;
  font-size: 0.9rem; font-weight: 500;
  padding: 6px 10px; border-radius: 9999px;
  transition: background 0.2s, color 0.2s;
}
.lien-accueil:hover { color: #fff; background: rgba(255, 255, 255, 0.12); }
</style>
