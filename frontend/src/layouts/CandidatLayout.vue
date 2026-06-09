<script setup>
import { ref, onMounted } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import api from '../api'

const auth = useAuthStore()
const router = useRouter()
const drawer = ref(false)
const annee = new Date().getFullYear()
const snack = ref({ show: false, color: 'success', text: '' })
const envoiEnCours = ref(false)

onMounted(() => auth.rafraichir())

async function renvoyerActivation() {
  envoiEnCours.value = true
  try {
    await api.post('/auth/renvoyer-verification/', { email: auth.utilisateur?.email })
    snack.value = { show: true, color: 'success', text: "Email d'activation renvoyé. Vérifiez votre boîte (et le spam)." }
  } catch {
    snack.value = { show: true, color: 'error', text: 'Envoi impossible, réessayez.' }
  } finally {
    envoiEnCours.value = false
  }
}

async function deconnexion() {
  await auth.deconnexion()
  router.push({ name: 'eligibles' })
}
</script>

<template>
  <div class="public">
    <header class="nav">
      <div class="nav-inner">
        <RouterLink :to="{ name: 'eligibles' }" class="logo">ACGT</RouterLink>

        <nav class="liens">
          <RouterLink :to="{ name: 'mes-dossiers' }" class="lien">Mes dossiers</RouterLink>
          <RouterLink :to="{ name: 'eligibles' }" class="lien">Candidats éligibles</RouterLink>
          <RouterLink :to="{ name: 'retenus-public' }" class="lien">Candidats retenus</RouterLink>
        </nav>

        <div class="d-flex align-center ga-2">
          <v-menu>
            <template #activator="{ props }">
              <button v-bind="props" class="compte">
                <v-avatar color="primary" size="34"><v-icon color="white" size="20">mdi-account</v-icon></v-avatar>
                <span class="compte-mail d-none d-md-inline">{{ auth.utilisateur?.email }}</span>
                <v-icon size="18" color="grey">mdi-chevron-down</v-icon>
              </button>
            </template>
            <v-list>
              <v-list-item :title="auth.utilisateur?.email" subtitle="Candidat" disabled />
              <v-divider />
              <v-list-item prepend-icon="mdi-logout" title="Déconnexion" @click="deconnexion" />
            </v-list>
          </v-menu>

          <button class="burger" @click="drawer = !drawer">☰</button>
        </div>
      </div>
      <transition name="fade">
        <nav v-if="drawer" class="liens-mobile">
          <RouterLink :to="{ name: 'mes-dossiers' }" @click="drawer = false">Mes dossiers</RouterLink>
          <RouterLink :to="{ name: 'eligibles' }" @click="drawer = false">Candidats éligibles</RouterLink>
          <RouterLink :to="{ name: 'retenus-public' }" @click="drawer = false">Candidats retenus</RouterLink>
          <a @click="deconnexion(); drawer = false">Déconnexion</a>
        </nav>
      </transition>
    </header>

    <main class="contenu">
      <v-alert v-if="auth.utilisateur && !auth.utilisateur.email_verifie"
               type="warning" variant="tonal" class="ma-4 mb-0" icon="mdi-email-alert">
        <div class="d-flex align-center flex-wrap ga-3">
          <span>Votre adresse email n'est pas encore vérifiée. Activez-la pour pouvoir déposer un dossier.</span>
          <v-spacer />
          <v-btn color="warning" variant="flat" size="small" :loading="envoiEnCours"
                 prepend-icon="mdi-email-sync" @click="renvoyerActivation">Renvoyer l'email d'activation</v-btn>
        </div>
      </v-alert>

      <router-view />
    </main>

    <footer class="pied-bas">
      © {{ annee }} Agence Congolaise des Grands Travaux (ACGT). Tous droits réservés.
    </footer>

    <v-snackbar v-model="snack.show" :color="snack.color" timeout="4000">{{ snack.text }}</v-snackbar>
  </div>
</template>

<style scoped>
.public { min-height: 100vh; display: flex; flex-direction: column; background: #F5F7FA; }
.nav { position: sticky; top: 0; z-index: 50; background: #fff; border-bottom: 1px solid #c6c5d4; }
.nav-inner { max-width: 1200px; margin: 0 auto; height: 64px; padding: 0 24px;
  display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.logo { font-size: 1.4rem; font-weight: 800; color: #1a237e; text-decoration: none; letter-spacing: 0.5px; }
.liens { display: flex; align-items: center; gap: 32px; }
.lien { color: #525f71; font-weight: 500; font-size: 0.9rem; text-decoration: none; transition: color 0.2s; padding-bottom: 2px; }
.lien:hover { color: #1a237e; }
.lien.router-link-active { color: #1a237e; font-weight: 700; border-bottom: 2px solid #1a237e; }
.compte { display: flex; align-items: center; gap: 8px; background: none; border: none; cursor: pointer; padding: 4px 8px; border-radius: 9999px; transition: background 0.2s; }
.compte:hover { background: #f5f2fb; }
.compte-mail { font-size: 0.85rem; font-weight: 600; color: #1f2933; }
.burger { display: none; background: none; border: none; font-size: 1.4rem; color: #1a237e; cursor: pointer; }
.liens-mobile { display: none; flex-direction: column; padding: 8px 24px 16px; background: #fff; border-top: 1px solid #eee; }
.liens-mobile a { padding: 10px 0; color: #1a237e; font-weight: 600; text-decoration: none; }
@media (max-width: 800px) { .liens { display: none; } .burger { display: block; } .liens-mobile { display: flex; } }
.contenu { flex-grow: 1; }
.pied-bas { background: #1a237e; color: #fff; text-align: center; padding: 18px; font-size: 0.8rem; opacity: 0.95; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
