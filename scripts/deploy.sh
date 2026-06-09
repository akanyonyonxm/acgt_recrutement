#!/bin/bash
# Déploiement sur le VPS recrutement.acgt.cd (167.71.45.222).
# Appelé par la CI (GitHub Actions) via SSH, ou lançable à la main sur le serveur :
#
#   ./scripts/deploy.sh
#
# Prérequis (une seule fois) : dépôt cloné, fichier .env présent à la racine,
# Docker + plugin Compose installés. Le certificat TLS est amorcé
# automatiquement au premier déploiement (voir étape 4).
set -euo pipefail

DOMAIN="recrutement.acgt.cd"
CERTBOT_VOLUME="acgt_certbot_conf"

# Se place à la racine du projet quel que soit le répertoire d'appel.
cd "$(dirname "$0")/.."

echo "### 1/5 Mise à jour du code (git pull)..."
git pull --ff-only

echo "### 2/5 Réseau Docker partagé..."
docker network inspect acgt_net >/dev/null 2>&1 || docker network create acgt_net

echo "### 3/5 Base de données PostgreSQL..."
docker compose -f docker-compose.db.yml up -d

echo "### 4/5 Certificat TLS..."
# Amorçage automatique au tout premier déploiement : si aucun certificat n'existe
# encore dans le volume, on lance init-letsencrypt.sh (qui émet le certificat et
# démarre Nginx). Les fois suivantes, le certificat est présent -> on saute
# (le renouvellement est géré par le conteneur certbot, pas ici).
if docker run --rm --entrypoint test -v "${CERTBOT_VOLUME}:/etc/letsencrypt" \
     certbot/certbot:latest -f "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"; then
  echo "  Certificat déjà présent."
else
  echo "  Aucun certificat -> amorçage Let's Encrypt..."
  chmod +x scripts/init-letsencrypt.sh
  ./scripts/init-letsencrypt.sh
fi

echo "### 5/5 Application (build + redémarrage)..."
# Les migrations + collectstatic + init_roles tournent au démarrage du backend
# (entrypoint.sh) : pas besoin de les lancer ici.
docker compose -f docker-compose.prod.yml up -d --build

echo "### Nettoyage des images orphelines..."
docker image prune -f

echo "### Déploiement terminé : https://${DOMAIN}"
