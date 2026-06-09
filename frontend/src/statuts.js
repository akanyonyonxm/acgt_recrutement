// Couleur Vuetify associée à chaque statut de dossier (chips, badges).
export const COULEUR_STATUT = {
  brouillon: 'grey',
  depose: 'warning',
  en_examen: 'info',
  retenu: 'success',
  non_retenu: 'error',
  rejete: 'error',
  // recommandations d'évaluation
  reserve: 'grey',
}

export function couleurStatut(statut) {
  return COULEUR_STATUT[statut] || 'grey'
}
