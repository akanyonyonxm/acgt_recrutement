<script setup>
import { ref } from 'vue'
import { RouterLink } from 'vue-router'

const drawer = ref(false)
const annee = new Date().getFullYear()
</script>

<template>
  <div class="public">
    <!-- Top nav -->
    <header class="nav">
      <div class="nav-inner">
        <RouterLink :to="{ name: 'eligibles' }" class="logo">ACGT</RouterLink>

        <nav class="liens">
          <RouterLink :to="{ name: 'eligibles' }" class="lien">Candidats éligibles</RouterLink>
          <RouterLink :to="{ name: 'retenus-public' }" class="lien">Candidats retenus</RouterLink>
        </nav>

        <div class="d-flex align-center ga-2">
          <RouterLink :to="{ name: 'candidat-connexion' }" class="btn-connexion">Connexion</RouterLink>
          <button class="burger" @click="drawer = !drawer">☰</button>
        </div>
      </div>
      <!-- menu mobile -->
      <transition name="fade">
        <nav v-if="drawer" class="liens-mobile">
          <RouterLink :to="{ name: 'eligibles' }" @click="drawer = false">Candidats éligibles</RouterLink>
          <RouterLink :to="{ name: 'retenus-public' }" @click="drawer = false">Candidats retenus</RouterLink>
          <RouterLink :to="{ name: 'candidat-connexion' }" @click="drawer = false">Connexion</RouterLink>
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
