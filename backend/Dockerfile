# Image de production du backend Django (servi par Gunicorn).
FROM python:3.12-slim

# Sorties Python non bufferisées (logs immédiats) ; pas de .pyc.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Dépendances système minimales (psycopg[binary] embarque libpq ; on garde
# l'image légère).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend

# Installe les dépendances Python d'abord (cache de couche Docker).
COPY backend/requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copie le code du backend. BASE_DIR = /app/backend ; MEDIA_ROOT = /app/fichiers_prives.
COPY backend/ ./

# Entrypoint : attend la base, applique migrations + collectstatic, lance Gunicorn.
COPY backend/entrypoint.sh /entrypoint.sh
# Normalise les fins de ligne (CRLF Windows -> LF) et rend exécutable.
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
