#!/bin/bash
# Amorçage du certificat Let's Encrypt pour recrutement.acgt.cd.
#
# À lancer UNE fois sur le VPS (167.71.45.222), après que le DNS pointe bien
# vers le serveur et que la base + le réseau partagé existent :
#
#   docker network create acgt_net                     # si pas déjà fait
#   docker compose -f docker-compose.db.yml up -d
#   ./scripts/init-letsencrypt.sh
#   docker compose -f docker-compose.prod.yml up -d
#
# Inspiré du script de référence wmnnd/nginx-certbot.
set -e

DOMAIN="recrutement.acgt.cd"
EMAIL="${LETSENCRYPT_EMAIL:-recrutement@acgt.cd}"   # surchargé via variable d'env
STAGING="${STAGING:-0}"                              # 1 = certificat de test (évite le rate-limit)

DATA_PATH="./certbot"
RSA_KEY_SIZE=4096

# Détecte `docker compose` (v2) ou `docker-compose` (v1) et cible le compose prod.
if docker compose version >/dev/null 2>&1; then
  COMPOSE="docker compose -f docker-compose.prod.yml"
else
  COMPOSE="docker-compose -f docker-compose.prod.yml"
fi

echo "### 1. Démarrage de Nginx avec un certificat factice (pour qu'il boote)..."

# Certificat auto-signé temporaire dans le volume certbot_conf via le conteneur certbot.
LIVE_PATH="/etc/letsencrypt/live/$DOMAIN"
$COMPOSE run --rm --entrypoint "\
  sh -c 'mkdir -p $LIVE_PATH && \
  openssl req -x509 -nodes -newkey rsa:$RSA_KEY_SIZE -days 1 \
    -keyout $LIVE_PATH/privkey.pem \
    -out $LIVE_PATH/fullchain.pem \
    -subj /CN=localhost'" certbot

echo "### 2. Démarrage de Nginx..."
$COMPOSE up -d web
sleep 3

echo "### 3. Suppression du certificat factice..."
$COMPOSE run --rm --entrypoint "\
  rm -rf /etc/letsencrypt/live/$DOMAIN \
  /etc/letsencrypt/archive/$DOMAIN \
  /etc/letsencrypt/renewal/$DOMAIN.conf" certbot

echo "### 4. Demande du vrai certificat Let's Encrypt..."

# Argument staging (certificat de test) le cas échéant.
STAGING_ARG=""
if [ "$STAGING" != "0" ]; then STAGING_ARG="--staging"; fi

$COMPOSE run --rm --entrypoint "\
  certbot certonly --webroot -w /var/www/certbot \
    $STAGING_ARG \
    --email $EMAIL \
    -d $DOMAIN \
    --rsa-key-size $RSA_KEY_SIZE \
    --agree-tos \
    --no-eff-email \
    --force-renewal" certbot

echo "### 5. Récupération des paramètres SSL recommandés (options-ssl + dhparams)..."
$COMPOSE run --rm --entrypoint "\
  sh -c 'wget -q -O /etc/letsencrypt/options-ssl-nginx.conf https://raw.githubusercontent.com/certbot/certbot/main/certbot-nginx/src/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf && \
  openssl dhparam -out /etc/letsencrypt/ssl-dhparams.pem 2048'" certbot

echo "### 6. Rechargement de Nginx avec le vrai certificat..."
$COMPOSE exec web nginx -s reload

echo
echo "### Terminé. HTTPS actif sur https://$DOMAIN"
echo "Lancez ensuite l'ensemble : $COMPOSE up -d"
