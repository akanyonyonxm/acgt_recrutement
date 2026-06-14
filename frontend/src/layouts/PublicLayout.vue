<script setup>
import { ref, onMounted } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useAppelsStore } from '../stores/appels'

const auth = useAuthStore()
const appels = useAppelsStore()
const router = useRouter()
const drawer = ref(false)
const annee = new Date().getFullYear()

// État de campagne partagé : réclamation + création de compte ne sont proposées
// que si des candidatures sont ouvertes. La connexion reste toujours possible
// (un candidat peut consulter ses dossiers même après la clôture).
onMounted(() => appels.charger())

async function deconnexion() {
  await auth.deconnexion()
  router.push({ name: 'eligibles' })
}
</script>

<template>
  <div class="public">
    <!-- Top nav -->
    <header class="nav">
      <div class="nav-inner">
        <RouterLink :to="{ name: 'eligibles' }" class="logo">ACGT</RouterLink>

        <nav class="liens">
          <RouterLink v-if="auth.estConnecte" :to="{ name: 'mes-dossiers' }" class="lien">Mes dossiers</RouterLink>
          <RouterLink :to="{ name: 'guide' }" class="lien">Comment postuler ?</RouterLink>
          <RouterLink :to="{ name: 'eligibles' }" class="lien">Candidats éligibles</RouterLink>
          <RouterLink :to="{ name: 'retenus-public' }" class="lien">Candidats retenus</RouterLink>
        </nav>

        <div class="d-flex align-center ga-2">
          <!-- Connecté : menu compte ; sinon : bouton Connexion -->
          <v-menu v-if="auth.estConnecte">
            <template #activator="{ props }">
              <button v-bind="props" class="compte">
                <v-avatar color="primary" size="34"><v-icon color="white" size="20">mdi-account</v-icon></v-avatar>
                <span class="compte-mail d-none d-md-inline">{{ auth.utilisateur?.email }}</span>
                <v-icon size="18" color="grey">mdi-chevron-down</v-icon>
              </button>
            </template>
            <v-list>
              <v-list-item :title="auth.utilisateur?.email"
                           :subtitle="auth.estAdmin ? 'Administrateur' : 'Candidat'" disabled />
              <v-divider />
              <v-list-item v-if="auth.estAdmin" prepend-icon="mdi-cog" title="Espace admin" :to="{ name: 'validation' }" />
              <v-list-item v-else prepend-icon="mdi-folder-account" title="Mes dossiers" :to="{ name: 'mes-dossiers' }" />
              <v-list-item prepend-icon="mdi-logout" title="Déconnexion" @click="deconnexion" />
            </v-list>
          </v-menu>
          <template v-else>
            <RouterLink v-if="appels.ouvertes" :to="{ name: 'reclamation' }" class="btn-reclamation">Réclamation</RouterLink>
            <RouterLink :to="{ name: 'candidat-connexion' }" class="btn-connexion">Connexion</RouterLink>
          </template>

          <button class="burger" @click="drawer = !drawer">☰</button>
        </div>
      </div>
      <!-- menu mobile -->
      <transition name="fade">
        <nav v-if="drawer" class="liens-mobile">
          <RouterLink v-if="auth.estConnecte" :to="{ name: 'mes-dossiers' }" @click="drawer = false">Mes dossiers</RouterLink>
          <RouterLink :to="{ name: 'guide' }" @click="drawer = false">Comment postuler ?</RouterLink>
          <RouterLink :to="{ name: 'eligibles' }" @click="drawer = false">Candidats éligibles</RouterLink>
          <RouterLink :to="{ name: 'retenus-public' }" @click="drawer = false">Candidats retenus</RouterLink>
          <RouterLink v-if="!auth.estConnecte && appels.ouvertes" :to="{ name: 'reclamation' }" @click="drawer = false">Réclamation</RouterLink>
          <RouterLink v-if="!auth.estConnecte" :to="{ name: 'candidat-connexion' }" @click="drawer = false">Connexion</RouterLink>
          <a v-else @click="deconnexion(); drawer = false">Déconnexion</a>
        </nav>
      </transition>
    </header>

    <main class="contenu"><router-view /></main>

    <footer class="pied-bas">
      © {{ annee }} Agence Congolaise des Grands Travaux (ACGT). Tous droits réservés.
    </footer>
  </div>
</template>

<style scoped>
.public { min-height: 100vh; display: flex; flex-direction: column; background: #F5F7FA; }

/* Nav */
.nav { position: sticky; top: 0; z-index: 50; background: #fff; border-bottom: 1px solid #c6c5d4; }
.nav-inner { max-width: 1200px; margin: 0 auto; height: 64px; padding: 0 24px;
  display: flex; align-items: center; justify-content: space-between; }
.logo { font-size: 1.4rem; font-weight: 800; color: #1a237e; text-decoration: none; letter-spacing: 0.5px; }
.liens { display: flex; align-items: center; gap: 32px; }
.lien { color: #525f71; font-weight: 500; font-size: 0.9rem; text-decoration: none; transition: color 0.2s; padding-bottom: 2px; }
.lien:hover { color: #1a237e; }
.lien.router-link-active { color: #1a237e; font-weight: 700; border-bottom: 2px solid #1a237e; }
.btn-connexion {
  background: #1a237e; color: #fff; padding: 8px 24px; border-radius: 9999px;
  font-weight: 700; font-size: 0.9rem; text-decoration: none; transition: all 0.2s;
}
.btn-connexion:hover { background: #283593; }
.btn-reclamation {
  background: #FDD835; color: #1a237e; padding: 8px 20px; border-radius: 9999px;
  font-weight: 700; font-size: 0.9rem; text-decoration: none; transition: all 0.2s;
}
.btn-reclamation:hover { background: #fbc02d; box-shadow: 0 6px 16px rgba(253,216,53,0.45); }
.compte { display: flex; align-items: center; gap: 8px; background: none; border: none; cursor: pointer; padding: 4px 8px; border-radius: 9999px; transition: background 0.2s; }
.compte:hover { background: #f5f2fb; }
.compte-mail { font-size: 0.85rem; font-weight: 600; color: #1f2933; }
.burger { display: none; background: none; border: none; font-size: 1.4rem; color: #1a237e; cursor: pointer; }
.material-i { display: none; }
.liens-mobile { display: none; flex-direction: column; padding: 8px 24px 16px; background: #fff; border-top: 1px solid #eee; }
.liens-mobile a { padding: 10px 0; color: #1a237e; font-weight: 600; text-decoration: none; }

@media (max-width: 800px) {
  .liens { display: none; }
  .burger { display: block; }
  .liens-mobile { display: flex; }
}

.contenu { flex-grow: 1; }

.pied-bas { background: #1a237e; color: #fff; text-align: center; padding: 18px; font-size: 0.8rem; opacity: 0.95; }

.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
