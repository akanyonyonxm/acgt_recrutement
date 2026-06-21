import { defineStore } from 'pinia'
import api from '../api'

// État public de la campagne : sert à savoir si les candidatures sont ouvertes
// (au moins un appel publié) et à afficher le dernier appel + son état.
// Chargé une fois (au montage du layout public), partagé par le header, la page
// des éligibles, etc.
export const useAppelsStore = defineStore('appels', {
  state: () => ({
    appels: [],
    charge: false, // true une fois /appels/ récupéré au moins une fois
  }),
  getters: {
    // Candidatures ouvertes : au moins un appel au statut « publié ».
    ouvertes: (s) => s.appels.some((a) => a.statut === 'publie'),
    // Dernier appel (le plus récent ; /appels/ est trié par -cree_le).
    dernierAppel: (s) => s.appels[0] || null,
    // Dépôt de recours ouvert : au moins un appel publié sans échéance ou dont
    // l'échéance n'est pas passée. Sinon, recours clôturés.
    recoursOuverts: (s) => {
      const pub = s.appels.filter((a) => a.liste_retenus_publiee)
      if (!pub.length) return false
      const now = Date.now()
      return pub.some((a) => !a.date_limite_recours || new Date(a.date_limite_recours).getTime() > now)
    },
  },
  actions: {
    async charger({ force = false } = {}) {
      if (this.charge && !force) return
      try {
        const { data } = await api.get('/appels/')
        this.appels = data.results
      } catch {
        this.appels = []
      } finally {
        this.charge = true
      }
    },
  },
})
