# Réinitialisation des données

Procédure pour **remettre à zéro les données opérationnelles** (entre deux cycles
de recrutement, ou pour effacer les données de démonstration après une mise en
service) **en conservant les comptes du personnel** (administrateurs / évaluateurs).

> ⚠️ **Opération destructive et manuelle.** Elle n'est **jamais** exécutée par la
> CI, le déploiement ni l'entrypoint (cf. règle impérative de `CLAUDE.md`). Elle se
> lance à la main, sur l'environnement concerné, par une personne habilitée.

## Ce qui est supprimé / conservé

| Supprimé | Conservé |
| --- | --- |
| Dossiers de candidature | Comptes **staff** : superusers, groupes **Administrateurs** et **Évaluateurs**, comptes `is_staff` |
| Pièces jointes (lignes **et fichiers** sur le disque) | Groupes / rôles |
| Historique de statuts, affectations, évaluations *(cascade des dossiers)* | Référentiels : **appels** à candidature, **postes**, **types de pièce** |
| Liste d'éligibilité *(sauf `--garder-eligibilite`)* | *(mots de passe du staff inchangés)* |
| File d'emails en attente, jetons email | |
| Comptes **candidats** (non-staff) | |

## Commande

`python manage.py reinitialiser_donnees`

| Option | Effet |
| --- | --- |
| *(aucune)* | **Aperçu** : affiche ce qui serait supprimé, **ne supprime rien** |
| `--confirmer` | Exécute réellement la suppression |
| `--garder-eligibilite` | Conserve la liste d'éligibilité importée |
| `--vider-appels` | Supprime **aussi** les appels à candidature (et leurs pièces exigées) |

## Procédure recommandée

### 1. Sauvegarder d'abord (fortement conseillé)

```bash
# Base de données (depuis la racine du projet, sur le VPS)
docker compose -f docker-compose.db.yml exec db \
  pg_dump -U acgt acgt_recrutement > sauvegarde_$(date +%F).sql
```

### 2. Aperçu (aucune suppression)

**Production (VPS, via Docker) :**

```bash
docker compose -f docker-compose.prod.yml exec backend \
  python manage.py reinitialiser_donnees
```

**Développement local :**

```bash
cd backend
venv/Scripts/python.exe manage.py reinitialiser_donnees
```

Vérifier les nombres affichés (dossiers, pièces, candidats, éligibilité) et la
ligne « Comptes staff conservés ».

### 3. Exécuter

```bash
# Production
docker compose -f docker-compose.prod.yml exec backend \
  python manage.py reinitialiser_donnees --confirmer

# Local
venv/Scripts/python.exe manage.py reinitialiser_donnees --confirmer
```

### Exemples courants

```bash
# Nouveau cycle : on efface les candidatures mais on garde la liste d'éligibilité
... reinitialiser_donnees --confirmer --garder-eligibilite

# Remise à zéro complète, y compris les appels à candidature
... reinitialiser_donnees --confirmer --vider-appels
```

## Après la réinitialisation

- Les comptes **admin / évaluateurs** et leurs mots de passe sont intacts.
- Les **rôles** (groupes) sont conservés ; au besoin, ré-exécuter `init_roles`
  (idempotent) ne fait pas de mal.
- Si vous avez utilisé `--vider-appels`, recréez un appel à candidature dans
  l'admin Django (`/console-3xfk2a/`) avant de rouvrir les dépôts.
- Pour réimporter une liste d'éligibilité : `import_eligibilite fichier.xlsx --publier`.

## Restaurer une sauvegarde (si besoin)

```bash
docker compose -f docker-compose.db.yml exec -T db \
  psql -U acgt acgt_recrutement < sauvegarde_AAAA-MM-JJ.sql
```
