import { defineStore } from 'pinia'
import api from '../api'

// Sait si le candidat peut encore postuler à au moins un appel publié.
export const useCandidatureStore = defineStore('candidature', {
  state: () => ({
    appels: [],
    mesAppelIds: new Set(),
    charge: false,
  }),
  getters: {
    // Au moins un appel publié non bloqué (multiple, ou unique pas encore postulé).
    peutPostuler: (s) =>
      s.appels.some(
        (a) => !(a.candidature_unique && s.mesAppelIds.has(a.id)),
      ),
  },
  actions: {
    async rafraichir() {
      try {
        const [{ data: da }, { data: dd }] = await Promise.all([
          api.get('/appels/'),
          api.get('/dossiers/'),
        ])
        this.appels = da.results.filter((a) => a.statut === 'publie')
        this.mesAppelIds = new Set(dd.results.map((d) => d.appel))
      } catch {
        // En cas d'erreur, on n'empêche pas l'accès (le serveur reste garant).
        this.appels = []
        this.mesAppelIds = new Set()
      } finally {
        this.charge = true
      }
    },
  },
})
