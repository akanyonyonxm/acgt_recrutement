import axios from 'axios'

// Client API partagé. Même origine via le proxy Vite : cookies de session
// envoyés automatiquement. Django attend le jeton CSRF en X-CSRFToken (lu
// depuis le cookie csrftoken) sur les requêtes non sûres.
const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
})

// À appeler au démarrage : pose le cookie CSRF avant toute requête POST.
export function initCsrf() {
  return api.get('/auth/csrf/')
}

export default api
