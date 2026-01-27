# Guide de Déploiement - CREATES Comptabilité

## Prérequis
- Compte GitHub (pour le code source)
- Compte sur la plateforme de déploiement choisie

---

## Option 1 : Render.com (Recommandé)

**Avantages :** Gratuit pour démarrer, PostgreSQL inclus, déploiement automatique depuis GitHub.

### Étapes :

1. **Pousser le code sur GitHub**
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/votre-username/creates-comptabilite.git
git push -u origin main
```

2. **Sur Render.com :**
   - Créer un compte sur https://render.com
   - Cliquer "New" → "Blueprint"
   - Connecter votre repo GitHub
   - Render détecte automatiquement `render.yaml`
   - Cliquer "Apply"

3. **Variables d'environnement** (automatiques avec render.yaml) :
   - `DATABASE_URL` : URL PostgreSQL (auto-générée)
   - `SECRET_KEY` : Clé secrète (auto-générée)

4. **Initialiser la base de données :**
   - Dans Render, aller dans le service web → Shell
   - Exécuter :
   ```bash
   python -c "from app import app, db; app.app_context().push(); db.create_all()"
   ```

---

## Option 2 : Railway.app

**Avantages :** Simple, $5/mois de crédits gratuits.

1. Connecter GitHub à Railway
2. Ajouter un service PostgreSQL
3. Définir les variables :
   - `DATABASE_URL` : copier depuis PostgreSQL
   - `SECRET_KEY` : générer avec `python -c "import secrets; print(secrets.token_hex(32))"`

---

## Option 3 : PythonAnywhere

**Avantages :** Gratuit pour apps légères, bon pour l'Afrique (serveurs EU).

1. Créer compte sur https://www.pythonanywhere.com
2. Uploader le code via "Files"
3. Créer une Web App → Flask → Python 3.10
4. Configurer le chemin WSGI
5. Utiliser MySQL (gratuit) au lieu de PostgreSQL

---

## Option 4 : VPS (DigitalOcean, Hetzner, OVH)

Pour plus de contrôle. Environ $5-10/mois.

```bash
# Sur le serveur Ubuntu
sudo apt update
sudo apt install python3-pip python3-venv nginx postgresql

# Créer l'environnement
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn

# Configurer PostgreSQL
sudo -u postgres createuser creates
sudo -u postgres createdb creates_compta -O creates

# Lancer avec Gunicorn
gunicorn --bind 0.0.0.0:8000 app:app

# Configurer Nginx comme reverse proxy
# Configurer systemd pour démarrage automatique
```

---

## Variables d'Environnement Requises

| Variable | Description | Exemple |
|----------|-------------|---------|
| `DATABASE_URL` | URL de connexion PostgreSQL | `postgresql://user:pass@host:5432/db` |
| `SECRET_KEY` | Clé secrète Flask (32+ caractères) | `votre-cle-secrete-tres-longue` |

### Générer une clé secrète :
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Migration SQLite → PostgreSQL

Pour passer de SQLite (dev) à PostgreSQL (prod) :

1. Exporter les données SQLite :
```bash
sqlite3 instance/ngo_accounting.db .dump > backup.sql
```

2. L'application détecte automatiquement `DATABASE_URL` pour PostgreSQL.

---

## Checklist Pré-Déploiement

- [ ] `requirements.txt` à jour
- [ ] `Procfile` présent
- [ ] `SECRET_KEY` différent de celui de développement
- [ ] Debug mode désactivé (`app.run(debug=False)`)
- [ ] Uploads configurés (stockage cloud si nécessaire)
- [ ] Backup automatique de la base de données

---

## Accès Initial

Après déploiement, créer le premier utilisateur :

```python
from app import app, db, Utilisateur
from werkzeug.security import generate_password_hash

with app.app_context():
    db.create_all()
    admin = Utilisateur(
        email='admin@creates.sn',
        nom='Administrateur',
        password_hash=generate_password_hash('VotreMotDePasseSecurise'),
        role='directeur',
        actif=True
    )
    db.session.add(admin)
    db.session.commit()
```

---

## Support

- Documentation Flask : https://flask.palletsprojects.com/
- Render.com Docs : https://render.com/docs
