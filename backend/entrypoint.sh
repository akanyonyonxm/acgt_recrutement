#!/bin/sh
set -e

# 1. Attendre que PostgreSQL accepte les connexions (la base tourne dans un
#    compose séparé : pas de depends_on possible entre les deux).
echo "Attente de PostgreSQL sur ${DB_HOST:-db}:${DB_PORT:-5432}..."
until python -c "import socket,os; s=socket.socket(); s.settimeout(2); s.connect((os.environ.get('DB_HOST','db'), int(os.environ.get('DB_PORT','5432'))))" 2>/dev/null; do
    echo "  ...indisponible, nouvelle tentative dans 2s"
    sleep 2
done
echo "PostgreSQL est prêt."

# 2. Migrations + statiques + rôles (idempotents).
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py init_roles
# Crée le compte admin depuis ADMIN_EMAIL/ADMIN_PASSWORD (.env), si définis.
python manage.py creer_admin

# 3. Lancer Gunicorn (3 workers ; ajuster selon les cœurs du VPS : 2*cpu+1).
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
