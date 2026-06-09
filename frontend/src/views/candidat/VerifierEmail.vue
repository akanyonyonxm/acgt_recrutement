<script setup>
import { ref, onMounted } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import api from '../../api'
import { useAuthStore } from '../../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const etat = ref('en_cours') // en_cours | ok | erreur
const message = ref('')
const compte = ref(4)

onMounted(async () => {
  const jeton = route.query.jeton
  if (!jeton) {
    etat.value = 'erreur'
    message.value = 'Lien de vérification invalide.'
    return
  }
  try {
    const { data } = await api.post('/auth/verifier-email/', { jeton })
    etat.value = 'ok'
    message.value = data.detail
    if (auth.estConnecte) await auth.rafraichir()
    // Redirection automatique : vers le dépôt si connecté, sinon la connexion.
    const dest = auth.estConnecte ? { name: 'postuler' } : { name: 'candidat-connexion' }
    const tic = setInterval(() => {
      compte.value -= 1
      if (compte.value <= 0) { clearInterval(tic); router.push(dest) }
    }, 1000)
  } catch (e) {
    etat.value = 'erreur'
    message.value = e.response?.data?.detail || 'Lien de vérification invalide ou expiré.'
  }
})
</script>

<template>
  <v-container class="py-16" style="max-width: 480px">
    <v-card class="pa-8 text-center">
      <template v-if="etat === 'en_cours'">
        <v-progress-circular indeterminate color="primary" size="48" class="mb-4" />
        <div>Vérification en cours…</div>
      </template>
      <template v-else-if="etat === 'ok'">
        <v-icon color="success" size="64" class="mb-3">mdi-check-circle</v-icon>
        <h2 class="text-h6 text-primary mb-2">Compte activé !</h2>
        <p class="text-body-2 mb-2">{{ message }}</p>
        <p class="text-caption text-medium-emphasis mb-4">Redirection dans {{ compte }} s…</p>
        <v-btn color="primary" variant="flat"
               :to="auth.estConnecte ? { name: 'postuler' } : { name: 'candidat-connexion' }">
          {{ auth.estConnecte ? 'Déposer un dossier' : 'Se connecter' }}
        </v-btn>
      </template>
      <template v-else>
        <v-icon color="error" size="64" class="mb-3">mdi-alert-circle</v-icon>
        <h2 class="text-h6 mb-2">Vérification impossible</h2>
        <p class="text-body-2 mb-4">{{ message }}</p>
        <v-btn color="primary" variant="text" :to="{ name: 'candidat-inscription' }">Recréer un compte</v-btn>
      </template>
    </v-card>
  </v-container>
</template>
