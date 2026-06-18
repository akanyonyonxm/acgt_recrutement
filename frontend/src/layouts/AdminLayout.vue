<script setup>
import { ref, computed } from 'vue'
import { useDisplay } from 'vuetify'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import logoBlanc from '../assets/acgt_logo_blanc.png'

const auth = useAuthStore()
const router = useRouter()
const { mobile } = useDisplay()
// Ouvert par défaut sur grand écran, replié (overlay) sur mobile.
const drawer = ref(!mobile.value)

const NAV = computed(() => [
  { to: { name: 'validation' }, icon: 'mdi-check-decagram-outline', t1: 'Validation', t2: 'des dossiers' },
  { to: { name: 'eligibilite' }, icon: 'mdi-account-multiple-check-outline', t1: 'Liste', t2: 'éligibilité' },
  { to: { name: 'reclamations' }, icon: 'mdi-account-alert-outline', t1: 'Réclamations', t2: "d'éligibilité" },
  { to: { name: 'appels' }, icon: 'mdi-bullhorn-outline', t1: 'Appels à', t2: 'candidature' },
  { to: { name: 'retenus' }, icon: 'mdi-trophy-outline', t1: 'Publication', t2: 'des retenus' },
  { to: { name: 'admin-recours' }, icon: 'mdi-gavel', t1: 'Recours', t2: 'des candidats' },
  { to: { name: 'rapports' }, icon: 'mdi-chart-box-outline', t1: 'Rapports', t2: '& statistiques' },
  // Gestion des accès : visible uniquement pour les administrateurs.
  ...(auth.estAdmin
    ? [{ to: { name: 'utilisateurs' }, icon: 'mdi-account-cog-outline', t1: 'Utilisateurs', t2: '& accès' }]
    : []),
])

const dateCourante = computed(() =>
  new Date().toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
)

async function deconnexion() {
  await auth.deconnexion()
  router.push({ name: 'connexion' })
}
</script>

<template>
  <v-navigation-drawer v-model="drawer" class="acgt-drawer" width="170"
                       :permanent="!mobile" :temporary="mobile">
    <div class="d-flex flex-column h-100">
      <div class="pa-4 d-flex justify-center brand-header">
        <div class="logo-box elevation-6">
          <img :src="logoBlanc" alt="ACGT" width="58" />
        </div>
      </div>

      <v-list class="pa-0 flex-grow-1 nav-scroll" nav density="comfortable">
        <v-list-item
          v-for="n in NAV"
          :key="n.t1"
          :to="n.to"
          active-class="nav-actif"
          class="nav-carre"
          height="92"
          @click="mobile && (drawer = false)"
        >
          <div class="d-flex flex-column align-center justify-center w-100 fill-height">
            <v-icon :icon="n.icon" size="26" class="mb-2" />
            <span class="nav-libelle">{{ n.t1 }}<br>{{ n.t2 }}</span>
          </div>
        </v-list-item>
      </v-list>

      <div class="pa-4 d-flex flex-column align-center ga-3">
        <v-avatar color="white" size="42" class="elevation-2">
          <v-icon icon="mdi-account" color="primary" size="26" />
          <v-tooltip activator="parent" location="end">{{ auth.utilisateur?.email }}</v-tooltip>
        </v-avatar>
        <v-tooltip location="end" text="Déconnexion">
          <template #activator="{ props }">
            <v-btn v-bind="props" icon="mdi-logout" variant="flat" color="red-lighten-1"
                   size="small" class="elevation-3" @click="deconnexion" />
          </template>
        </v-tooltip>
      </div>
    </div>
  </v-navigation-drawer>

  <v-app-bar color="white" elevation="1" height="68">
    <v-app-bar-nav-icon color="primary" @click="drawer = !drawer" />
    <v-toolbar-title class="text-primary font-weight-bold">
      ACGT — Traitement des candidatures
    </v-toolbar-title>
    <v-spacer />
    <div class="mr-6 text-body-2 text-medium-emphasis d-none d-md-flex align-center bg-grey-lighten-4 px-4 py-2 rounded-pill">
      <v-icon size="small" class="mr-2" color="primary">mdi-calendar-month</v-icon>
      <span class="font-weight-medium text-capitalize">{{ dateCourante }}</span>
    </div>
  </v-app-bar>

  <v-main class="bg-grey-lighten-4">
    <v-container fluid class="pa-6 pa-md-8">
      <router-view />
    </v-container>
  </v-main>
</template>

<style scoped>
.acgt-drawer {
  background: linear-gradient(180deg, #1a237e 0%, #0d1b2a 100%) !important;
  border: none;
}
.brand-header { background: linear-gradient(to bottom, rgba(255,255,255,0.06), transparent); }
.logo-box {
  width: 74px; height: 74px;
  border-radius: 18px;
  background: rgba(255,255,255,0.12);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255,255,255,0.2);
  display: flex; align-items: center; justify-content: center;
}
/* La liste défile si elle dépasse (min-height:0 requis pour un enfant flex). */
.nav-scroll {
  overflow-y: auto;
  min-height: 0;
  scrollbar-width: thin;
  scrollbar-color: rgba(255,255,255,0.3) transparent;
}
.nav-scroll::-webkit-scrollbar { width: 6px; }
.nav-scroll::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.25); border-radius: 3px; }
.nav-scroll::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.4); }
.nav-carre {
  border-bottom: 1px solid rgba(255,255,255,0.06);
  border-radius: 0 !important;
  color: #B0BEC5 !important;
}
.nav-carre:hover { background: rgba(255,255,255,0.06); color: #fff !important; }
.nav-actif { background: #0277BD !important; color: #fff !important; }
.nav-actif :deep(.v-icon) { color: #fff !important; }
.nav-libelle {
  font-size: 0.72rem; font-weight: 700; text-transform: uppercase;
  text-align: center; line-height: 1.2;
}
</style>
