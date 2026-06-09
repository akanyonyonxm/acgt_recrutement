#!/bin/bash
# Amorçage du certificat Let's Encrypt pour recrutement.acgt.cd.
#
# Appelé automatiquement par scripts/deploy.sh au tout premier déploiement
# (quand aucun certificat n'existe). Lançable aussi à la main :
#
#   ./scripts/init-letsencrypt.sh                 # vrai certificat
#   STAGING=1 ./scripts/init-letsencrypt.sh       # certificat de test (rate-limit large)
#
# Méthode STANDALONE : Certbot ouvre lui-même le port 80 et répond au challenge,
# SANS Nginx. On évite ainsi le cercle vicieux « Nginx a besoin du certificat
# pour démarrer, mais le certificat a besoin de Nginx pour être validé ».
# Le renouvellement, lui, se fait en webroot via Nginx (conteneur certbot du
# compose) une fois le site en ligne.
#
# Prérequis : le DNS recrutement.acgt.cd doit pointer vers ce serveur, et le
# port 80 doit être joignable depuis Internet (pare-feu / firewall cloud ouvert).
set -e

DOMAIN="recrutement.acgt.cd"
EMAIL="${LETSENCRYPT_EMAIL:-recrutement@acgt.cd}"   # surchargé via variable d'env
STAGING="${STAGING:-0}"                              # 1 = certificat de test
CERTBOT_CONF="acgt_certbot_conf"                     # volume partagé avec Nginx
CERTBOT_WWW="acgt_certbot_www"

# Détecte `docker compose` (v2) ou `docker-compose` (v1) et cible le compose prod.
if docker compose version >/dev/null 2>&1; then
  COMPOSE="docker compose -f docker-compose.prod.yml"
else
  COMPOSE="docker-compose -f docker-compose.prod.yml"
fi

STAGING_ARG=""
if [ "$STAGING" != "0" ]; then STAGING_ARG="--staging"; fi

echo "### 1. Libération du port 80 (arrêt de Nginx s'il tourne)..."
$COMPOSE stop web 2>/dev/null || true

echo "### 2. Demande du certificat Let's Encrypt (mode standalone)..."
# Certbot écoute lui-même sur le port 80 (publié via -p) et sert le challenge.
# Le certificat est écrit dans le volume partagé avec Nginx.
docker run --rm \
  -p 80:80 \
  -v "${CERTBOT_CONF}:/etc/letsencrypt" \
  -v "${CERTBOT_WWW}:/var/www/certbot" \
  certbot/certbot:latest certonly --standalone \
    $STAGING_ARG \
    --non-interactive --agree-tos --no-eff-email \
    --email "$EMAIL" \
    -d "$DOMAIN"

echo "### 3. Démarrage de Nginx avec le certificat..."
$COMPOSE up -d web

echo
echo "### Terminé. Certificat en place pour $DOMAIN"
