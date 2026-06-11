#!/bin/bash
# Sauvegarde de la base PostgreSQL ET des documents (pièces jointes) du projet ACGT.
#
# Opération NON destructive (lecture seule) : à lancer MANUELLEMENT sur le serveur,
# ou via cron. Ne fait JAMAIS partie du pipeline de déploiement.
#
#   ./scripts/sauvegarde.sh
#
# Variables (facultatives, surchargeables) :
#   BACKUP_DIR        dossier des sauvegardes      (défaut : /srv/acgt_backups)
#   RETENTION_JOURS   purge des sauvegardes au-delà (défaut : 30 jours)
# DB_USER / DB_NAME sont lus depuis le fichier .env (racine du projet).
set -euo pipefail

# Racine du projet, quel que soit le répertoire d'appel.
cd "$(dirname "$0")/.."

# Lit UNE variable du .env sans exécuter le fichier. On ne « source » pas le
# .env : c'est un fichier clé=valeur (style Django), où des valeurs peuvent
# contenir des espaces (ex. « ACGT Recrutement ») que bash interpréterait comme
# des commandes. On extrait donc seulement les clés utiles, en retirant les
# guillemets éventuels et le retour chariot Windows (\r).
val_env() {
  grep -E "^$1=" .env 2>/dev/null | tail -n1 | cut -d'=' -f2- \
    | sed -e 's/\r$//' -e 's/^"\(.*\)"$/\1/' -e "s/^'\(.*\)'$/\1/"
}

DB_USER="${DB_USER:-$(val_env DB_USER)}"; DB_USER="${DB_USER:-acgt}"
DB_NAME="${DB_NAME:-$(val_env DB_NAME)}"; DB_NAME="${DB_NAME:-acgt_recrutement}"
BACKUP_DIR="${BACKUP_DIR:-/srv/acgt_backups}"
RETENTION_JOURS="${RETENTION_JOURS:-30}"
MEDIA_VOLUME="acgt_media_data"
HORODATAGE="$(date +%F_%H%M%S)"

mkdir -p "$BACKUP_DIR"

echo "### 1/3 Base de données -> ${BACKUP_DIR}/db_${HORODATAGE}.sql.gz"
# pg_dump dans le conteneur de la base (compose dédié), compressé à la volée.
docker compose -f docker-compose.db.yml exec -T db \
  pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "${BACKUP_DIR}/db_${HORODATAGE}.sql.gz"

echo "### 2/3 Documents (volume ${MEDIA_VOLUME}) -> ${BACKUP_DIR}/media_${HORODATAGE}.tgz"
# Archive le volume des pièces jointes en lecture seule.
docker run --rm -v "${MEDIA_VOLUME}:/data:ro" -v "${BACKUP_DIR}:/backup" alpine \
  tar czf "/backup/media_${HORODATAGE}.tgz" -C /data .

echo "### 3/3 Rotation : suppression des sauvegardes de plus de ${RETENTION_JOURS} jours"
find "$BACKUP_DIR" -maxdepth 1 -name 'db_*.sql.gz' -mtime +"${RETENTION_JOURS}" -delete
find "$BACKUP_DIR" -maxdepth 1 -name 'media_*.tgz' -mtime +"${RETENTION_JOURS}" -delete

echo "### Sauvegarde terminée. Contenu de ${BACKUP_DIR} :"
ls -lh "$BACKUP_DIR"
