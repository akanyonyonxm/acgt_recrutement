# acgt_recrutement

Plateforme web de traitement des dossiers d'**appel à candidature (AAC)** pour
l'Agence Congolaise des Grands Travaux (ACGT).

- **Backend** : Django 6 + Django REST Framework (apps `comptes`, `candidatures`).
- **Frontend** : Vue 3 + Vite + Vuetify 3 + Pinia.
- **Production** : Docker (PostgreSQL, Gunicorn, Nginx + TLS Let's Encrypt) sur
  `recrutement.acgt.cd`.

## Démarrage (développement)

```bash
# Backend (http://localhost:8000)
cd backend
venv/Scripts/python.exe manage.py migrate
venv/Scripts/python.exe manage.py runserver

# Frontend (http://localhost:5173)
cd frontend
npm install
npm run dev
```

## Déploiement

Voir [DEPLOIEMENT.md](DEPLOIEMENT.md) (Docker Compose + CI/CD GitHub Actions).
Les conventions et l'architecture sont décrites dans [CLAUDE.md](CLAUDE.md).
