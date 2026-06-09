# --- Étape 1 : build du front Vue 3 (Vite) ---
FROM node:22-alpine AS build

WORKDIR /app

# Dépendances (cache de couche : copie des manifestes d'abord).
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Code + build de production -> /app/dist
COPY frontend/ ./
RUN npm run build

# --- Étape 2 : Nginx sert la SPA + reverse-proxy vers le backend + TLS ---
FROM nginx:1.27-alpine

# Le build statique de Vue.
COPY --from=build /app/dist /usr/share/nginx/html

# La configuration du serveur (proxy /api,/admin,... + SSL) est montée en
# volume depuis ./nginx/conf.d au runtime (modifiable sans rebuild).
# On retire la conf par défaut pour éviter tout conflit de server_name.
RUN rm -f /etc/nginx/conf.d/default.conf

EXPOSE 80 443
