# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Plateforme web de traitement des dossiers d'**appel à candidature (AAC)** pour l'ACGT. Des personnes éligibles (anciens stagiaires / candidats) déposent un dossier en ligne ; l'ACGT le valide puis l'examine. Cible de production : VPS Linux (Django + Vue), ~200–1000 dossiers par campagne. **Le code, les modèles et les commentaires sont rédigés en français** — conserver cette convention.

Statut actuel : **en production** sur `recrutement.acgt.cd` (Django + Vue, PostgreSQL, Docker). Sont en place et déployés : cycle de vie (statuts) des dossiers, authentification (email/vérification/reset), service d'emails (Resend), pièces jointes, dépôt candidat, liste d'éligibilité (import Excel + recherche tolérante), back-office de validation, **réclamations d'éligibilité**, **recours**, **répartition/équilibrage de la charge** entre agents, **rapports & statistiques**, et les espaces SPA public / candidat / back-office. L'**examen évaluateur** (désignation/avis) existe mais le flux courant valide en direct (validateur). Restent côté « prévu » : email de convocation en masse (`EmailQueue` non branché), bascule MinIO/S3, durcissement RGPD.

## Commandes

Toutes les commandes se lancent depuis `backend/`. Sur Windows, l'interpréteur du venv est `venv\Scripts\python.exe` (en bash : `venv/Scripts/python.exe`).

```bash
cd backend
venv/Scripts/python.exe manage.py migrate              # appliquer les migrations
venv/Scripts/python.exe manage.py makemigrations       # après modif des modèles
venv/Scripts/python.exe manage.py runserver            # API sur http://localhost:8000
venv/Scripts/python.exe manage.py init_roles           # crée les 6 groupes de roles.py (idempotent)
venv/Scripts/python.exe manage.py createsuperuser      # compte admin technique (demande l'email, pas un username)
venv/Scripts/python.exe manage.py check                # vérification système
venv/Scripts/python.exe manage.py makemigrations --check --dry-run   # aucune migration en attente (pré-déploiement)
```

API navigable DRF : `http://localhost:8000/api/` · Admin Django (technique) : `http://localhost:8000/console-3xfk2a/` (URL discrète, renommée depuis `/admin/` pour ne pas entrer en conflit avec l'espace de traitement Vue). **Espaces SPA** : `/traitement` = connexion agent/admin (URL à saisir, non liée publiquement) ; `/gestion/*` = back-office (validation, dossiers, éligibilité, appels, retenus) ; `/candidat/*` = espace candidat. Le proxy Vite/Nginx proxifie `/api`, `/console-3xfk2a`, `/static`, `/media` vers Django ; tout le reste (`/gestion`, `/traitement`, `/candidat`…) est servi par le SPA.

Dépendances : `venv/Scripts/python.exe -m pip install -r requirements.txt`.

Données de démo + comptes de test : `venv/Scripts/python.exe seed_demo.py` (admin `admin@acgt.cd` / `Admin2026!`).

**Tests** : `tests.py` est vide ; la vérification se fait par **scripts autonomes** lancés directement (pas `manage.py test`, qui pose des soucis de pipe/CSRF sous Windows). Modèle : un fichier `_t_*.py` à la racine de `backend/` qui fait `os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings'); django.setup()`, `settings.ALLOWED_HOSTS += ['testserver']`, puis `APIClient().force_authenticate(...)` + assertions manuelles, sur des données préfixées `ZZ`/`ZTEST` nettoyées en fin de script. Lancer avec `PYTHONIOENCODING=utf-8` (caractères accentués/→ en console Windows), supprimer le fichier après.

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

Les rôles sont portés par des **groupes Django** (`roles.py`, 6 groupes : `Administrateurs`, `Superviseurs`, `Évaluateurs`, `Correcteurs`, `Validateurs`, `Lecteurs`) ; un superuser cumule tout. **Toujours** passer par les helpers de `roles.py` (jamais tester un groupe en dur) — ce sont les points de décision uniques :

- `acces_backoffice(u)` : CONSULTATION (voir tous dossiers/réclamations/liste) — tout rôle back-office.
- `peut_traiter(u)` : faire avancer un dossier/réclamation (admin, superviseur, validateur).
- `peut_superviser(u)` : actions de supervision (répartir la charge, publier, désigner) — admin + superviseur, **pas** un simple validateur.
- `peut_decider_affecte(u, affecte_a_id)` : trancher selon l'affectation — admin/superviseur toujours ; un validateur **uniquement son lot** (`affecte_a == lui`).
- `est_admin` / `est_correcteur` : domaine réservé admin (comptes, import liste, modification d'identité/code/noms).

`rejeter` et `non-retenir` exigent un `motif` non vide. `_transition(..., lier_eligibilite, email)` factorise : `approuver` accepte un `eligibilite_id` optionnel (rattache `Dossier.ligne_eligibilite`) et notifie ; chaque transition envoie son email via `_notifier` (best-effort, n'annule jamais la transition). La file de validation côté back-office = `GET /api/dossiers/?statut=depose`.

### Dépôt candidat & pièces jointes

`DossierViewSet.get_queryset()` **scope par rôle** : admin → tout ; **évaluateur → uniquement les dossiers où il est désigné** (`affectations__evaluateur=user`) + les siens ; candidat → ses dossiers (`deposant=user`). Ne jamais retirer ce filtre. Le dépôt est un flux : `POST /api/dossiers/` (crée un BROUILLON, `deposant`=user, exige `email_verifie`) → `POST .../pieces/` (ajout, propriétaire + brouillon uniquement) → `DELETE .../pieces/<id>/` → `POST .../soumettre/` (vérifie `pieces_obligatoires_manquantes()`, passe en DÉPOSÉ, envoie l'accusé). Après soumission le dossier n'est plus modifiable (`Dossier.modifiable`).

Les **pièces jointes** (`PieceJointe`) sont stockées sous `MEDIA_ROOT` (privé, hors web root) avec un nom de fichier UUID non devinable (`chemin_piece_jointe`). **Jamais d'URL publique** : le seul accès est `GET .../pieces/<id>/telecharger/` (authentifié + scopé), qui renvoie un `FileResponse`. Extensions (`EXTENSIONS_AUTORISEES`) et taille (`TAILLE_MAX_PIECE`, 5 Mo) validées à l'upload.

### Répartition des responsabilités d'interface (décision structurante)

- **Django Admin** = configuration et inspection technique uniquement (utilisateurs, AAC, référentiels/listes déroulantes, critères de validation). Les `Dossier` et les `Recours` y sont **en lecture seule** — ne pas y ajouter d'édition métier (l'édition d'un recours, par ex., se fait dans le back-office Vue, pas dans la console).
- **Le front Vue** porte tout le métier visible : espaces public, candidat, et back-office (validation, réclamations, recours, rapports).

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

### Réclamations d'éligibilité (`ReclamationEligibilite`)

Flux public pour qui ne trouve pas son nom : formulaire (identité libre + poste souhaité + email + justificatifs `DocumentReclamation` stockés hors web root, UUID) → l'agent consulte les documents puis **valide** ou **rejette**. À la **validation**, un `Dossier` (`deposant=None`) est créé puis mené à `RETENU` via `changer_statut` (l'invariant de la machine à états est respecté), avec `reclamation.dossier_cree` posé. Une **grille de critères** configurable (`CritereValidation`, par portée réclamation/dossier/les_deux) est cochée à la décision et historisée (`ControleCritere`, avec copie du libellé) ; tous les critères actifs doivent être cochés, sauf **dérogation admin** justifiée. `rouvrir` (superviseur) ramène EN_ATTENTE pour correction : si elle était validée, le dossier créé est **annulé** (passé à REJETÉ) **et `dossier_cree` remis à `None`**.

### Recours (`Recours`)

Après publication, une personne lésée recherche son **nom** (réclamations + dossiers soumis, dédupliqués), reconnaît son enregistrement et y **lie** son recours (FK `dossier` OU `reclamation`, SET_NULL), avec date de naissance (vérification d'identité), email, message. Back-office dédié (`RecoursViewSet`, `/gestion/recours`) : `rechercher`/`create` publics (throttle) ; `personne` (back-office) renvoie tous les dossiers/réclamations homonymes + leurs documents + le **motif de rejet** (dossier : dernier `HistoriqueStatut` vers rejeté/non-retenu ; réclamation : `motif`). Décision `valider`/`rejeter` (motif obligatoire au rejet), **gardée par l'affectation** (`peut_decider_affecte`) ; `valider` est une décision interne (n'altère pas le dossier source ni la liste publiée). L'**édition** d'un recours est réservée aux **administrateurs**.

### Répartition / équilibrage de la charge (`affecte_a`)

`Dossier`, `ReclamationEligibilite` et `Recours` portent un FK `affecte_a` (agent chargé du traitement). Action `repartir` (superviseur) : round-robin **équitable** sur le sous-ensemble filtré, `seulement_non_affectes` (défaut) vs **rééquilibrage**. Éligibilité des agents selon la catégorie visée : file en cours → `peut_traiter` ; catégorie **déjà décidée** (révision) → `peut_superviser` seulement. Pour les **recours**, la répartition **regroupe par identité normalisée** : tous les doublons d'une personne vont au **même** agent (round-robin sur les personnes). Action `repartition` : charge par agent (back-office). Le filtre `affecte` (`moi`/`aucune`/`<id>`) scope les listes.

### Rapports & provenance des dossiers (`RapportsView`)

`GET /api/rapports/?appel=` (back-office) agrège éligibles, dossiers, réclamations, **recours**, retenus par poste/origine et niveaux de traitement — **hors brouillon**. Distinction structurante côté dossiers : `deposant` est le **discriminant fiable et permanent** de la provenance (un vrai dépôt en ligne a toujours un `deposant` ; un dossier né d'une validation de réclamation a `deposant=None`). Le lien `dossier_cree`, lui, est **effacé à l'annulation**. `RapportsView` expose donc `dossiers.par_categorie` (hors brouillon) : **en_ligne** (`deposant` renseigné = vrais dépôts, c'est le chiffre « Déposés en ligne » du tableau de bord), **validation** (`deposant=None` + encore lié, actif), **annule** (`deposant=None` + orphelin = résidu d'une réclamation rouverte). Ne pas rebaser cette distinction sur `dossier_cree` (qui sous-estime les ajouts et gonfle les « en ligne »).

### Liste d'éligibilité & recherche tolérante

`ListeEligibilite` est importée d'Excel (`python manage.py import_eligibilite fichier.xlsx [--vider] [--publier]`, colonnes nom/postnom/prenom/type/annee/reference). À l'enregistrement, `save()` calcule `texte_recherche` = `normaliser_texte("nom postnom prenom")` (`utils.py` : sans accents, minuscules, espaces simples) ; l'import en masse via `bulk_create` doit donc remplir `texte_recherche` lui-même (bulk_create contourne `save()`).

La recherche (`EligibiliteViewSet`, `?q=`) découpe la requête en tokens normalisés et exige que **chaque** token soit `__contains` dans `texte_recherche` → tolérante aux accents/casse/ordre, et partielle. C'est volontairement « contient », pas du flou (une faute de frappe type lettre manquante ne matche pas) ; le ranking trigram (`pg_trgm`) est une amélioration prod future. Scoping : public → `est_publie=True` + serializer **NOM/POSTNOM/PRÉNOM seulement** ; admin → toute la liste + `reference` interne. Ne jamais exposer `reference` côté public.

### Frontend Vue (espace admin — `frontend/src/`)

SPA **Vue 3 + Vuetify 3 + Vue Router + Pinia**. Design system aligné sur `D:\Workspace\naaxym\profilis\profilis_frontend` (autre projet ACGT) : thème dans `plugins/vuetify.js` — **primary `#1a237e` (bleu nuit), accent `#FDD835` (jaune), secondary `#0d1b2a`** ; icônes MDI (`@mdi/font`) ; logo `src/assets/acgt_logo*.png`. Layout = drawer dégradé bleu à items carrés (icône + libellé), app-bar blanche avec pastille date, `v-main` gris clair (cf. `layouts/AdminLayout.vue`). Couleurs de statut → chips Vuetify dans `statuts.js`.

Auth par **session** : `api.js` (axios) avec `withCredentials` + `xsrfHeaderName: 'X-CSRFToken'` ; `stores/auth.js` appelle `initCsrf()` puis `/auth/moi/` au démarrage (gardes de route dans `router/index.js` ; getters `peutTraiter`/`peutSuperviser`/`accesBackoffice`/`estAdmin`/`estValidateur` reflètent les helpers `roles.py`). Espaces construits : **public** (`views/public/` : éligibles, retenus, recours, réclamation, guide), **candidat** (`views/candidat/`), **back-office** (`views/admin/` : `Validation.vue`, `DossierDetail.vue`, `Reclamations.vue`, `RecoursAdmin.vue`, `Rapports.vue`, `Appels.vue`, `Retenus.vue`). Téléchargement/aperçu de pièce = même origine via proxy (`?inline=1` pour l'aperçu, sans le param = pièce jointe).

Conventions front réutilisées partout : filtres mémorisés en `localStorage` avec clé **suffixée par l'id utilisateur** (`acgt_filtres_<page>_<uid>`) ; `v-data-table-server` rechargé via une `cle` computed concaténant les filtres (passée en `:search`) ; cartes `StatCard` cliquables pour filtrer ; un validateur voit **son lot** par défaut (`affecte='moi'`). Normaliser l'affichage des noms exotiques avec `String(v).normalize('NFKC')`.

### Configuration

`config/settings.py` lit `.env` (via `python-dotenv`) — voir `.env.example`. Bascules par variables d'environnement, **sans changer le code** :

- **Base** : SQLite par défaut (dev) → PostgreSQL si `DB_ENGINE=postgresql`. La prod vise PostgreSQL (recherche tolérante future via `unaccent` / `pg_trgm`).
- **Fichiers privés** : `MEDIA_ROOT` pointe vers `fichiers_prives/` **hors de la racine web** (pièces jointes sensibles). Démarrage en stockage local ; bascule MinIO/S3 prévue via `django-storages` (API S3) sans toucher au code métier.

## Décisions métier figées (invariants à conserver)

- **Candidature libre** : un proche peut postuler à la place de quelqu'un (le `deposant` peut différer de la personne nommée ; identité saisie librement).
- **Pas de « complément demandé »** : l'agent approuve ou rejette, sans aller-retour.
- **Anti-triche par le NOM** : rattachement/correspondance d'éligibilité sur nom+postnom+prénom normalisés, **jamais sur le code seul** (un candidat peut saisir le code d'autrui).
- **Listes publiques en lecture seule** : éligibles et retenus (NOM/POSTNOM/PRÉNOM only) ; le bouton « Postuler »/« Recours » est séparé ; `reference` interne jamais exposée.
- **Confidentialité candidat** : l'espace candidat ne montre que le premier et le dernier statut (jamais les étapes intermédiaires ni les noms d'agents), et « En cours de traitement » tant que la liste n'est pas publiée.

## Reste à faire

Email de convocation **en masse** via `EmailQueue` (`envoyer_emails_en_attente`, cron — infrastructure en place, non branchée), bascule stockage **MinIO/S3** via `django-storages`, ranking trigram (`pg_trgm`/`unaccent`) en prod, durcissement RGPD (conservation/purge).
