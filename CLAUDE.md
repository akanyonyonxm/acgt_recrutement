# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Plateforme web de traitement des dossiers d'**appel à candidature (AAC)** pour l'ACGT. Des personnes éligibles (anciens stagiaires / candidats) déposent un dossier en ligne ; l'ACGT le valide puis l'examine. Cible de production : VPS Linux (Django + Vue), ~200–1000 dossiers par campagne. **Le code, les modèles et les commentaires sont rédigés en français** — conserver cette convention.

Statut actuel : backend Django (apps `comptes` + `candidatures`). Sont en place : le **cycle de vie (statuts) des dossiers**, l'**authentification** (comptes email, vérification, reset), et le **service d'emails** (Resend). Pas encore : front Vue 3, pièces jointes, dépôt candidat, liste d'éligibilité, examen évaluateur — voir le plan dans `C:\Users\akany\.claude\plans\` et « Périmètre prévu ».

## Commandes

Toutes les commandes se lancent depuis `backend/`. Sur Windows, l'interpréteur du venv est `venv\Scripts\python.exe` (en bash : `venv/Scripts/python.exe`).

```bash
cd backend
venv/Scripts/python.exe manage.py migrate              # appliquer les migrations
venv/Scripts/python.exe manage.py makemigrations       # après modif des modèles
venv/Scripts/python.exe manage.py runserver            # API sur http://localhost:8000
venv/Scripts/python.exe manage.py init_roles           # crée les groupes Administrateurs/Évaluateurs (idempotent)
venv/Scripts/python.exe manage.py createsuperuser      # compte admin technique (demande l'email, pas un username)
venv/Scripts/python.exe manage.py check                # vérification système
venv/Scripts/python.exe manage.py test                 # tests (tests.py vide pour l'instant)
venv/Scripts/python.exe manage.py test candidatures.tests.NomDuTest   # un seul test
```

API navigable DRF : `http://localhost:8000/api/` · Admin Django (technique) : `http://localhost:8000/console-3xfk2a/` (URL discrète, renommée depuis `/admin/` pour ne pas entrer en conflit avec l'espace de traitement Vue). **Espaces SPA** : `/traitement` = connexion agent/admin (URL à saisir, non liée publiquement) ; `/gestion/*` = back-office (validation, dossiers, éligibilité, appels, retenus) ; `/candidat/*` = espace candidat. Le proxy Vite/Nginx proxifie `/api`, `/console-3xfk2a`, `/static`, `/media` vers Django ; tout le reste (`/gestion`, `/traitement`, `/candidat`…) est servi par le SPA.

Dépendances : `venv/Scripts/python.exe -m pip install -r requirements.txt`.

Données de démo + comptes de test : `venv/Scripts/python.exe seed_demo.py` (admin `admin@acgt.cd` / `Admin2026!`).

### Frontend (Vue 3 + Vite, dans `frontend/`)

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173 (proxifie /api, /console-3xfk2a, /media, /static vers :8000 ; /gestion, /traitement, /candidat servis par le SPA)
npm run build    # build de production dans dist/
```
Lancer **les deux** serveurs (Django sur 8000, Vite sur 5173) pour le dev. Le proxy Vite rend l'API même-origine → cookies de session + CSRF sans CORS.

## Déploiement & données (règle impérative)

Le déploiement automatique (CI/CD GitHub Actions → `scripts/deploy.sh`, lui-même appelé à chaque push sur `main`) ne doit **JAMAIS détruire ni écraser les données ni les documents**. Les données (base PostgreSQL) et les documents (pièces jointes) vivent dans des **volumes Docker persistants** (`acgt_pgdata`, `acgt_media_data`) qui survivent aux redéploiements — ne jamais les recréer/supprimer dans le pipeline.

- **Interdit en CI / dans `deploy.sh` / dans `entrypoint.sh`** : tout ce qui détruit ou remet à zéro — `docker compose down -v` (suppression de volumes), `flush`, suppression/`delete()` en masse, `import_eligibilite --vider`, `seed_demo.py` / `seed_eligibles.py`, réinitialisation du mot de passe admin (`ADMIN_RESET_PASSWORD=True`), purge de `fichiers_prives/`, ou toute migration destructrice de données.
- **Autorisé en CI (automatique)** : uniquement des opérations **additives et idempotentes** — `migrate` (migrations non destructrices), `collectstatic`, `init_roles`, `creer_admin` (crée le compte s'il manque, **ne réécrase pas** le mot de passe).
- **Opérations destructrices ou d'initialisation** (remplacement de la liste d'éligibilité, seed de démo, reset de mot de passe, purge, restauration) : les placer dans des **scripts séparés, lancés MANUELLEMENT** sur le serveur (jamais dans le pipeline ni l'entrypoint).

Avant d'ajouter une étape au déploiement, vérifier qu'elle est non destructrice ; en cas de doute, en faire un script manuel.

### Vérification avant CHAQUE déploiement (obligatoire)

À refaire systématiquement avant tout push sur `main` (qui déclenche le déploiement) :

1. **Pipeline DB-safe** — aucune commande destructive dans `.github/`, `scripts/`, `backend/entrypoint.sh`, `backend/Dockerfile`, `docker-compose*.yml`. Contrôle rapide (doit ne **rien** renvoyer) :
   ```bash
   grep -rniE "down -v|flush|seed|--vider|ADMIN_RESET_PASSWORD|loaddata|delete\(\)|drop|truncate" \
     .github/ scripts/ backend/entrypoint.sh backend/Dockerfile docker-compose*.yml
   ```
   `deploy.sh` ne fait que `git reset --hard origin/main`, `docker compose ... up -d` (jamais `down -v`), build et `image prune`. `entrypoint.sh` ne fait que `migrate` / `collectstatic` / `init_roles` / `creer_admin` (ce dernier **ne réécrase pas** le mot de passe). Les volumes `acgt_pgdata` et `acgt_media_data` ne sont jamais recréés/supprimés.
2. **Mêmes vérifs que la CI, en local** : `manage.py check`, `manage.py makemigrations --check --dry-run` (aucune migration en attente), `npm run build` (front).
3. **Migrations additives uniquement** — relire toute nouvelle migration : pas de `RunPython` qui supprime/écrase des données, pas de suppression de champ porteur de données en prod.

Tant que ces trois points sont verts, le déploiement ne peut pas toucher aux données.

## Architecture

Le système repose sur **une machine à états** : le dossier de candidature et son cycle de vie sont le cœur de tout. Comprendre `candidatures/models.py` + `views.py` + `roles.py` ensemble est nécessaire pour être productif.

### Le workflow de statuts (invariant central)

```
BROUILLON ──soumettre (candidat)──► DÉPOSÉ ──approuver (admin)──► EN_EXAMEN ──retenir (éval.)──► RETENU
                                       │                              └──non-retenir (éval.)──► NON_RETENU
                                       └──rejeter (admin)──────────────────────────────────────► REJETÉ
```

Un dossier naît en `BROUILLON` (le candidat ajoute/retire ses pièces) ; `soumettre` valide la complétude puis le verrouille en `DÉPOSÉ`.

`RETENU / NON_RETENU / REJETÉ` sont terminaux. Règles à respecter impérativement :

- **Le statut ne se modifie JAMAIS par écriture directe.** Le champ `statut` est en `read_only` dans le serializer et dans l'admin. Tout changement passe par `Dossier.changer_statut(nouveau, par, motif)`, qui valide la transition contre `Dossier.TRANSITIONS` et lève `ValidationError` si elle est interdite.
- **Toute transition est journalisée** dans `HistoriqueStatut` (qui / quoi / quand / motif) — traçabilité RGPD. Ne pas contourner `changer_statut`, sinon l'audit est perdu.
- Ajouter un statut = modifier l'enum `Dossier.Statut` **et** le dict `TRANSITIONS` (+ `STATUTS_TERMINAUX`) de façon cohérente.

### Couche API et rôles

Les transitions sont exposées comme **actions DRF dédiées** sur `DossierViewSet` (`approuver`, `rejeter`, `retenir`, `non-retenir`), pas via PATCH. La méthode privée `_transition()` factorise : contrôle du rôle → validation du motif → appel modèle → réponse. Pour ajouter une transition, ajouter une `@action` qui délègue à `_transition`.

Les rôles sont portés par des **groupes Django** (`roles.py` : `Administrateurs`, `Évaluateurs`) ; un superuser cumule tout. `est_admin()` / `est_evaluateur()` sont les seuls points de décision d'autorisation — les réutiliser plutôt que de tester les groupes en dur. `rejeter` et `non-retenir` exigent un `motif` non vide. `_transition(..., lier_eligibilite, email)` factorise : `approuver` accepte un `eligibilite_id` optionnel (rattache `Dossier.ligne_eligibilite` pour la traçabilité) et notifie le candidat ; chaque transition envoie son email via `_notifier` (best-effort, n'annule jamais la transition). La file de validation côté back-office = `GET /api/dossiers/?statut=depose` (le staff voit tout).

### Dépôt candidat & pièces jointes

`DossierViewSet.get_queryset()` **scope par rôle** : admin → tout ; **évaluateur → uniquement les dossiers où il est désigné** (`affectations__evaluateur=user`) + les siens ; candidat → ses dossiers (`deposant=user`). Ne jamais retirer ce filtre. Le dépôt est un flux : `POST /api/dossiers/` (crée un BROUILLON, `deposant`=user, exige `email_verifie`) → `POST .../pieces/` (ajout, propriétaire + brouillon uniquement) → `DELETE .../pieces/<id>/` → `POST .../soumettre/` (vérifie `pieces_obligatoires_manquantes()`, passe en DÉPOSÉ, envoie l'accusé). Après soumission le dossier n'est plus modifiable (`Dossier.modifiable`).

Les **pièces jointes** (`PieceJointe`) sont stockées sous `MEDIA_ROOT` (privé, hors web root) avec un nom de fichier UUID non devinable (`chemin_piece_jointe`). **Jamais d'URL publique** : le seul accès est `GET .../pieces/<id>/telecharger/` (authentifié + scopé), qui renvoie un `FileResponse`. Extensions (`EXTENSIONS_AUTORISEES`) et taille (`TAILLE_MAX_PIECE`, 5 Mo) validées à l'upload.

### Répartition des responsabilités d'interface (décision structurante)

- **Django Admin** = configuration et inspection technique uniquement (utilisateurs, AAC, référentiels/listes déroulantes). Les `Dossier` y sont **en lecture seule** — ne pas y ajouter d'édition métier.
- **Le futur front Vue** portera tout le métier visible : espaces public, candidat, back-office admin (validation) et **espace évaluateur** (poste de travail de notation sur mesure).

### Comptes & authentification (`comptes/`)

Modèle utilisateur **personnalisé** `comptes.User` (`AUTH_USER_MODEL`) : l'**email est l'identifiant** de connexion (pas de username), avec un `UserManager` dédié. Conséquence : ne jamais importer `django.contrib.auth.models.User` — utiliser `get_user_model()` / `settings.AUTH_USER_MODEL`. Candidats = utilisateurs auto-inscrits hors groupes staff ; admin/évaluateurs = utilisateurs dans les groupes de `roles.py`.

Auth par **session Django** (cookie) ; le front récupère le cookie CSRF via `GET /api/auth/csrf/` puis envoie `X-CSRFToken` sur les POST authentifiés. Endpoints sous `/api/auth/` : `inscription`, `verifier-email`, `connexion`, `deconnexion`, `moi`, `mot-de-passe/demande`, `mot-de-passe/reinitialiser`. La vérification d'email et le reset passent par `JetonEmail` (UUID à usage unique, expiration 48 h, `JetonEmail.emettre()` invalide les anciens). Les endpoints anti-énumération (`demande` de reset, renvoi de vérification) répondent toujours de façon neutre.

### Service d'emails (`candidatures/services/email.py`)

Point d'entrée unique `envoyer_email(destinataire, sujet, template, contexte)`. Bascule automatique : `RESEND_API_KEY` défini → envoi réel via l'API HTTP Resend ; sinon → **backend console** (dev/tests, affichage terminal). Ne jamais appeler Resend directement. Templates dans `candidatures/templates/emails/` (`base.html` + un fichier par email). Les emails liés aux comptes sont construits dans `comptes/emails.py` (lien front via `FRONTEND_URL`).

Régime d'envoi : transactionnel **direct** (accusé, décision individuelle). L'infrastructure d'envoi **en masse via `EmailQueue`** + `python manage.py envoyer_emails_en_attente --limite N` (cron, pour rester sous la limite Resend) est en place mais **pas encore branchée** — réservée au futur email de convocation à la publication (voir ci-dessous).

### Publication des retenus

`POST /api/appels/<id>/publier-retenus/` (admin) met `liste_retenus_publiee=True` → affichage public. **Aucun email** envoyé à la publication pour l'instant : le retenu a déjà reçu l'email de décision via l'action `retenir`. L'email de convocation à la publication (2ᵉ mail, en masse via `EmailQueue`) est volontairement différé. La liste publique est `RetenusViewSet` (`GET /api/retenus/?appel=&q=`, AllowAny) : uniquement les RETENU d'un AAC publié, en **NOM/POSTNOM/PRÉNOM** (recherche tolérante via `Dossier.texte_recherche`, calculé dans `Dossier.save()`).

### Examen évaluateur (désignation vs validation)

Règle centrale : **être désigné** (`AffectationEvaluateur`) donne l'accès en consultation ; seuls les désignés avec **`peut_valider=True`** changent le statut. `_verifier_designe()` garde `evaluations` (avis), `_verifier_validateur()` garde `retenir`/`non-retenir` (via `_transition(..., verif_validateur=True)`). L'`Evaluation` (avis + recommandation, **pas de note chiffrée**) est consultative et distincte du changement de statut ; un évaluateur a au plus une évaluation par dossier (upsert). L'admin désigne via `POST .../affectations/` (et Django Admin inline) ; `retenir`/`non-retenir` envoient l'email de décision.

### Liste d'éligibilité & recherche tolérante

`ListeEligibilite` est importée d'Excel (`python manage.py import_eligibilite fichier.xlsx [--vider] [--publier]`, colonnes nom/postnom/prenom/type/annee/reference). À l'enregistrement, `save()` calcule `texte_recherche` = `normaliser_texte("nom postnom prenom")` (`utils.py` : sans accents, minuscules, espaces simples) ; l'import en masse via `bulk_create` doit donc remplir `texte_recherche` lui-même (bulk_create contourne `save()`).

La recherche (`EligibiliteViewSet`, `?q=`) découpe la requête en tokens normalisés et exige que **chaque** token soit `__contains` dans `texte_recherche` → tolérante aux accents/casse/ordre, et partielle. C'est volontairement « contient », pas du flou (une faute de frappe type lettre manquante ne matche pas) ; le ranking trigram (`pg_trgm`) est une amélioration prod future. Scoping : public → `est_publie=True` + serializer **NOM/POSTNOM/PRÉNOM seulement** ; admin → toute la liste + `reference` interne. Ne jamais exposer `reference` côté public.

### Frontend Vue (espace admin — `frontend/src/`)

SPA **Vue 3 + Vuetify 3 + Vue Router + Pinia**. Design system aligné sur `D:\Workspace\naaxym\profilis\profilis_frontend` (autre projet ACGT) : thème dans `plugins/vuetify.js` — **primary `#1a237e` (bleu nuit), accent `#FDD835` (jaune), secondary `#0d1b2a`** ; icônes MDI (`@mdi/font`) ; logo `src/assets/acgt_logo*.png`. Layout = drawer dégradé bleu à items carrés (icône + libellé), app-bar blanche avec pastille date, `v-main` gris clair (cf. `layouts/AdminLayout.vue`). Couleurs de statut → chips Vuetify dans `statuts.js`.

Auth par **session** : `api.js` (axios) avec `withCredentials` + `xsrfHeaderName: 'X-CSRFToken'` ; `stores/auth.js` appelle `initCsrf()` puis `/auth/moi/` au démarrage (garde de route dans `router/index.js`, `meta.role: 'admin'`). Seul l'espace **admin** est construit (`views/admin/`) : `Validation.vue` (v-data-table, filtres), `DossierDetail.vue` (pièces, recherche d'éligibilité + rattachement, approuver/rejeter, désignation d'évaluateurs, avis, historique), `Appels.vue`, `Retenus.vue`. Espaces public/candidat/évaluateur à faire. Téléchargement de pièce = lien `<a href="/api/dossiers/<id>/pieces/<pid>/telecharger/">` (même origine via proxy).

### Configuration

`config/settings.py` lit `.env` (via `python-dotenv`) — voir `.env.example`. Bascules par variables d'environnement, **sans changer le code** :

- **Base** : SQLite par défaut (dev) → PostgreSQL si `DB_ENGINE=postgresql`. La prod vise PostgreSQL (recherche tolérante future via `unaccent` / `pg_trgm`).
- **Fichiers privés** : `MEDIA_ROOT` pointe vers `fichiers_prives/` **hors de la racine web** (pièces jointes sensibles). Démarrage en stockage local ; bascule MinIO/S3 prévue via `django-storages` (API S3) sans toucher au code métier.

## Périmètre prévu (non encore codé)

`PieceJointe` (upload hors web root), `ListeEligibilite` (import Excel + recherche tolérante, double publication publique éligibles/retenus), dépôt candidat (création de dossiers en `DÉPOSÉ`, bloqué si incomplet), `Evaluation` (notation évaluateur), emails transactionnels via **Resend** (API HTTP, domaine `recrutement.acgt.cd`), et le front **Vue 3 + Vite + Pinia**. Décisions métier figées à garder en tête : candidature **libre** (un proche peut postuler à la place de quelqu'un), pas de « complément demandé » (l'admin approuve ou rejette), liste publique des éligibles **en lecture seule** (le bouton « Postuler » est séparé).
