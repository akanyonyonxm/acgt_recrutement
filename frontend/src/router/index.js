import { ref } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

// Indique qu'une navigation est en cours (barre de progression en haut).
export const navEnCours = ref(false)

const routes = [
  { path: '/', redirect: '/eligibles' },
  {
    path: '/',
    component: () => import('../layouts/PublicLayout.vue'),
    meta: { public: true },
    children: [
      {
        path: 'eligibles',
        name: 'eligibles',
        component: () => import('../views/public/Eligibles.vue'),
      },
      {
        path: 'retenus',
        name: 'retenus-public',
        component: () => import('../views/public/RetenusPublic.vue'),
      },
    ],
  },
  {
    // Accès agent/admin : URL discrète à saisir manuellement (non liée publiquement).
    path: '/traitement',
    name: 'connexion',
    component: () => import('../views/Login.vue'),
    meta: { public: true },
  },
  // Espace candidat
  {
    path: '/candidat/inscription',
    name: 'candidat-inscription',
    component: () => import('../views/candidat/Inscription.vue'),
    meta: { public: true },
  },
  {
    path: '/candidat/connexion',
    name: 'candidat-connexion',
    component: () => import('../views/candidat/Connexion.vue'),
    meta: { public: true },
  },
  {
    path: '/candidat/verifier-email',
    name: 'verifier-email',
    component: () => import('../views/candidat/VerifierEmail.vue'),
    meta: { public: true },
  },
  {
    path: '/candidat',
    component: () => import('../layouts/CandidatLayout.vue'),
    meta: { auth: 'candidat' },
    children: [
      { path: '', redirect: '/candidat/mes-dossiers' },
      { path: 'mes-dossiers', name: 'mes-dossiers', component: () => import('../views/candidat/MesDossiers.vue') },
      { path: 'postuler', name: 'postuler', component: () => import('../views/candidat/Postuler.vue') },
      { path: 'dossiers/:id', name: 'dossier-candidat', component: () => import('../views/candidat/DossierCandidat.vue') },
    ],
  },
  {
    path: '/gestion',
    component: () => import('../layouts/AdminLayout.vue'),
    meta: { role: 'admin' },
    children: [
      { path: '', redirect: '/gestion/validation' },
      {
        path: 'validation',
        name: 'validation',
        component: () => import('../views/admin/Validation.vue'),
      },
      {
        path: 'dossiers/:id',
        name: 'dossier',
        component: () => import('../views/admin/DossierDetail.vue'),
      },
      {
        path: 'eligibilite',
        name: 'eligibilite',
        component: () => import('../views/admin/Eligibilite.vue'),
      },
      {
        path: 'appels',
        name: 'appels',
        component: () => import('../views/admin/Appels.vue'),
      },
      {
        path: 'retenus',
        name: 'retenus',
        component: () => import('../views/admin/Retenus.vue'),
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  navEnCours.value = true
  const auth = useAuthStore()
  if (!auth.charge) await auth.initialiser()

  if (to.meta.public) return true

  // Espace candidat : toute personne connectée.
  if (to.meta.auth === 'candidat') {
    if (!auth.estConnecte) {
      return { name: 'candidat-connexion', query: { suite: to.fullPath } }
    }
    return true
  }

  // Espace agent/admin.
  if (!auth.estConnecte) {
    return { name: 'connexion', query: { suite: to.fullPath } }
  }
  if (to.meta.role === 'admin' && !auth.estAdmin) {
    return { name: 'connexion' }
  }
  return true
})

router.afterEach(() => { navEnCours.value = false })
router.onError(() => { navEnCours.value = false })

export default router
