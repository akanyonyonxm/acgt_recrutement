import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// En dev, on proxifie /api, /admin et /media vers Django : le front et l'API
// sont alors vus comme une même origine (pas de CORS, cookies de session OK).
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/admin': 'http://localhost:8000',
      '/media': 'http://localhost:8000',
    },
  },
})
