import { defineStore } from 'pinia'
import api, { initCsrf } from '../api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    utilisateur: null,
    charge: false, // true une fois la session vérifiée au démarrage
  }),
  getters: {
    estConnecte: (s) => !!s.utilisateur,
    estAdmin: (s) => s.utilisateur?.roles?.includes('admin') ?? false,
    estEvaluateur: (s) => s.utilisateur?.roles?.includes('evaluateur') ?? false,
    estCorrecteur: (s) => s.utilisateur?.roles?.includes('correcteur') ?? false,
    estValidateur: (s) => s.utilisateur?.roles?.includes('validateur') ?? false,
    estLecteur: (s) => s.utilisateur?.roles?.includes('lecteur') ?? false,
    // Peut faire changer les étapes (approuver/rejeter, valider une réclamation…).
    peutTraiter() { return this.estAdmin || this.estValidateur },
    // Accès au back-office (en lecture au minimum).
    accesBackoffice() {
      return this.estAdmin || this.estValidateur || this.estCorrecteur || this.estLecteur
    },
  },
  actions: {
    // Vérifie s'il y a déjà une session active (au lancement de l'app).
    async initialiser() {
      await initCsrf()
      try {
        const { data } = await api.get('/auth/moi/')
        this.utilisateur = data
      } catch {
        this.utilisateur = null
      } finally {
        this.charge = true
      }
    },
    // Re-synchronise le profil (ex. après vérification de l'email).
    async rafraichir() {
      try {
        const { data } = await api.get('/auth/moi/')
        this.utilisateur = data
      } catch {
        this.utilisateur = null
      }
    },
    async connexion(email, motDePasse) {
      const { data } = await api.post('/auth/connexion/', {
        email,
        mot_de_passe: motDePasse,
      })
      this.utilisateur = data
      return data
    },
    async deconnexion() {
      try {
        await api.post('/auth/deconnexion/')
      } finally {
        this.utilisateur = null
      }
    },
  },
})
