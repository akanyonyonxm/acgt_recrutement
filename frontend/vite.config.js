import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// En dev, on proxifie /api, /console-3xfk2a (admin Django), /media et /static
// vers Django : le front et l'API sont vus comme une même origine (pas de CORS,
// cookies OK). NB : /gestion n'est PAS proxifié — c'est l'espace de traitement
// (SPA), servi par Vite (sinon l'actualisation renverrait un 404 Django).
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/console-3xfk2a': 'http://localhost:8000',
      '/media': 'http://localhost:8000',
      '/static': 'http://localhost:8000',
    },
  },
})
