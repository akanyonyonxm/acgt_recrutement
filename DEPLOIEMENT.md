# Déploiement — recrutement.acgt.cd (VPS 167.71.45.222)

Déploiement Docker en deux fichiers compose :

- **`docker-compose.db.yml`** — PostgreSQL 16 (volume persistant `acgt_pgdata`).
- **`docker-compose.prod.yml`** — l'application (production) :
  - `backend` — Django + Gunicorn (migrations + `collectstatic` + `init_roles` au démarrage) ;
  - `web` — Nginx : sert la SPA Vue (build Vite), proxifie `/api`, `/admin`, `/static`, `/media` vers le backend, termine le TLS ;
  - `certbot` — Let's Encrypt : émission initiale + **renouvellement automatique**.

Les deux compose communiquent via le réseau Docker partagé **`acgt_net`** et lisent le même fichier **`.env`** (racine).

## Prérequis

1. Docker + plugin Compose installés sur le VPS.
2. Le DNS de `recrutement.acgt.cd` pointe vers `167.71.45.222` (enregistrement A) — **indispensable avant d'émettre le certificat**.
3. Ports 80 et 443 ouverts (pare-feu / `ufw`).

## Première mise en service

```bash
# 1. Récupérer le code sur le VPS, se placer à la racine du projet.
cd acgt_recrutement

# 2. Configurer l'environnement de production.
cp .env.prod.example .env
nano .env            # SECRET_KEY, DB_PASSWORD, RESEND_API_KEY, etc.

# 3. Créer le réseau partagé (une seule fois).
docker network create acgt_net

# 4. Démarrer la base.
docker compose -f docker-compose.db.yml up -d

# 5. Émettre le certificat TLS (démarre aussi Nginx).
chmod +x scripts/init-letsencrypt.sh
./scripts/init-letsencrypt.sh
#   Astuce : tester d'abord sans toucher au rate-limit Let's Encrypt :
#   STAGING=1 ./scripts/init-letsencrypt.sh   (puis relancer sans STAGING)

# 6. Démarrer l'ensemble de l'application.
docker compose -f docker-compose.prod.yml up -d --build
```

L'application est en ligne sur **<https://recrutement.acgt.cd>**.

Créer un compte admin technique :

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

## Renouvellement SSL (automatique)

Aucune action manuelle nécessaire :

- le conteneur **`certbot`** tente un `certbot renew` **toutes les 12 h** (no-op tant que le certificat expire dans plus de 30 jours) ;
- le conteneur **`web`** (Nginx) recharge sa configuration **toutes les 6 h** pour servir tout certificat fraîchement renouvelé.

Forcer un renouvellement / vérifier l'état :

```bash
docker compose -f docker-compose.prod.yml run --rm certbot renew --force-renewal
docker compose -f docker-compose.prod.yml exec web nginx -s reload
docker compose -f docker-compose.prod.yml run --rm certbot certificates    # dates d'expiration
```

## Mises à jour applicatives

### Automatique — CI/CD GitHub Actions (recommandé)

Le workflow [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml) déploie à chaque
push sur `main` : il vérifie d'abord (checks Django + cohérence des migrations + build front),
puis se connecte au VPS en SSH et exécute [`scripts/deploy.sh`](scripts/deploy.sh)
(`git pull` → réseau → base → `docker compose up -d --build` → purge des images).
Déclenchable aussi à la main depuis l'onglet **Actions**.

**Préparation (une seule fois) :**

1. Pousser le dépôt sur GitHub (`git init`, `git remote add origin …`, `git push`).
2. Sur le VPS : cloner le dépôt dans le dossier de déploiement, créer le `.env`,
   et amorcer le TLS (`init-letsencrypt.sh`) — cf. « Première mise en service ».
3. Générer une clé SSH dédiée au déploiement et autoriser sa clé publique sur le VPS :

   ```bash
   ssh-keygen -t ed25519 -C "github-deploy" -f deploy_key   # ne pas committer deploy_key
   ssh-copy-id -i deploy_key.pub deploy_user@167.71.45.222
   ```

4. Dans le dépôt GitHub → **Settings → Secrets and variables → Actions**, ajouter :

   - `DEPLOY_HOST` — `167.71.45.222`
   - `DEPLOY_USER` — l'utilisateur SSH (ex. `deploy`)
   - `DEPLOY_SSH_KEY` — le contenu de la clé **privée** `deploy_key`
   - `DEPLOY_PATH` — chemin du dépôt sur le VPS (ex. `/srv/acgt_recrutement`)
   - `DEPLOY_PORT` — port SSH (facultatif, défaut `22`)

   Astuce : l'« environnement » GitHub `production` (référencé dans le workflow)
   permet d'exiger une approbation manuelle avant chaque déploiement.

### Manuelle (sur le VPS, sans CI)

```bash
./scripts/deploy.sh
# équivaut à :
git pull
docker compose -f docker-compose.prod.yml up -d --build   # rebuild backend + front, migrations auto
```

La base n'est pas touchée (compose séparé). Pour la mettre à jour : `docker compose -f docker-compose.db.yml ...`.

## Opérations courantes

```bash
docker compose -f docker-compose.prod.yml logs -f backend           # logs Django/Gunicorn
docker compose -f docker-compose.prod.yml logs -f web               # logs Nginx
docker compose -f docker-compose.prod.yml exec backend python manage.py migrate   # migrations manuelles
docker compose -f docker-compose.db.yml exec db \
  pg_dump -U acgt acgt_recrutement > sauvegarde.sql                 # backup base
```

## Sécurité — points clés

- La base **n'expose aucun port** sur l'hôte : joignable uniquement par le backend via `acgt_net`.
- Les **pièces jointes** (`media_data`) restent privées : servies seulement via l'endpoint authentifié Django, jamais en direct par Nginx.
- En prod (`DEBUG=False`) : cookies `Secure`, redirection HTTPS, HSTS 1 an activés dans `settings.py`.
- Le `.env` réel et le dossier `certbot/` ne sont pas versionnés.
