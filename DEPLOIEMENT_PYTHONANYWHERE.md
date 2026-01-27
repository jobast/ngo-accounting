# Guide de Déploiement sur PythonAnywhere

## Étape 1: Créer un Compte PythonAnywhere

1. Allez sur https://www.pythonanywhere.com
2. Cliquez sur "Start running Python online in less than a minute!"
3. Créez un compte gratuit (Beginner)
4. Notez bien votre **username** (vous en aurez besoin)

## Étape 2: Uploader les Fichiers

### Option A: Via Git (recommandé)

1. Dans PythonAnywhere, ouvrez un **Bash console**
2. Clonez votre repository:
   ```bash
   git clone https://github.com/votre-repo/ngo-accounting.git
   cd ngo-accounting
   ```

### Option B: Via Upload Manuel

1. Cliquez sur **"Files"** dans le menu
2. Créez un dossier `ngo-accounting`
3. Uploadez tous les fichiers:
   - `app.py`
   - `requirements.txt`
   - `pythonanywhere_wsgi.py`
   - Dossier `templates/` (avec tous les sous-dossiers)
   - Dossier `static/` (si vous en avez un)

## Étape 3: Installer les Dépendances

1. Ouvrez un **Bash console**
2. Créez un environnement virtuel:
   ```bash
   cd ngo-accounting
   python3.10 -m venv venv
   source venv/bin/activate
   ```

3. Installez les packages:
   ```bash
   pip install -r requirements.txt
   ```

⚠️ **Si vous avez des erreurs avec `psycopg2-binary`** (normal sur plan gratuit):
```bash
pip install -r requirements.txt --no-deps
pip install flask flask-sqlalchemy flask-login flask-limiter werkzeug openpyxl python-dotenv
```

## Étape 4: Initialiser la Base de Données

Dans le **Bash console**:
```bash
cd ~/ngo-accounting
source venv/bin/activate
python3 << EOF
from app import app, db
with app.app_context():
    from app import init_db
    init_db()
EOF
```

Vous devriez voir: "Base de données initialisée avec succès!"

## Étape 5: Configurer l'Application Web

1. Cliquez sur **"Web"** dans le menu
2. Cliquez sur **"Add a new web app"**
3. Choisissez **"Manual configuration"** (pas "Flask")
4. Sélectionnez **Python 3.10**
5. Cliquez sur "Next"

### Configuration du WSGI

1. Dans la section "Code", cliquez sur le lien du fichier WSGI (ex: `/var/www/votreusername_pythonanywhere_com_wsgi.py`)
2. **Supprimez tout le contenu** du fichier
3. Copiez-collez le contenu de `pythonanywhere_wsgi.py`
4. **IMPORTANT:** Modifiez la ligne:
   ```python
   username = 'votreusername'  # ← Remplacez par votre vrai username
   ```
5. Sauvegardez (Ctrl+S ou bouton "Save")

### Configuration du Virtualenv

1. Retournez sur la page **"Web"**
2. Dans la section "Virtualenv", cliquez sur "Enter path to a virtualenv"
3. Entrez:
   ```
   /home/votreusername/ngo-accounting/venv
   ```
   (Remplacez `votreusername` par votre username)
4. Cliquez sur le ✓ pour valider

### Configuration des Fichiers Statiques (Optionnel)

Si vous avez un dossier `static/`:

1. Dans la section "Static files", cliquez sur "Enter URL" et "Enter path"
2. URL: `/static/`
3. Path: `/home/votreusername/ngo-accounting/static/`

## Étape 6: Lancer l'Application

1. En haut de la page **"Web"**, cliquez sur le bouton vert **"Reload"**
2. Attendez quelques secondes
3. Cliquez sur le lien de votre application (ex: `votreusername.pythonanywhere.com`)

## Connexion

Utilisez les identifiants par défaut:
- **Email:** `admin@creates.sn`
- **Mot de passe:** `admin123`

⚠️ **Changez ce mot de passe immédiatement!**

## Étape 7: Configuration de Sécurité

### Générer une SECRET_KEY sécurisée

1. Dans un **Bash console**:
   ```bash
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```

2. Copiez la clé générée

3. Modifiez votre fichier WSGI:
   - Allez dans **"Web" > fichier WSGI**
   - Remplacez `CHANGEZ_CE_SECRET_EN_PRODUCTION_123456789` par la clé générée
   - Sauvegardez
   - Cliquez sur **"Reload"**

## Sauvegardes

Pour sauvegarder votre base de données:

1. **Bash console**:
   ```bash
   cd ~/ngo-accounting/instance
   cp ngo_accounting.db ngo_accounting_$(date +%Y%m%d).db
   ```

2. Téléchargez le fichier via **"Files"**

⏰ **Recommandation:** Faites une sauvegarde **hebdomadaire** manuellement.

## Dépannage

### L'application ne se charge pas
- Vérifiez les logs: **Web > Log files > Error log**
- Vérifiez que le virtualenv est bien configuré
- Vérifiez que le username dans le WSGI est correct

### "ImportError: No module named app"
- Vérifiez le chemin dans le fichier WSGI
- Vérifiez que `app.py` est bien dans `/home/votreusername/ngo-accounting/`

### "Database is locked"
- Rare avec 2-3 utilisateurs
- Si ça arrive: attendez 30 secondes et réessayez

## Limites du Plan Gratuit

- ✓ Parfait pour 2-3 utilisateurs
- ✓ Application toujours active (pas de sleep)
- ⚠️ 512 MB de stockage (largement suffisant)
- ⚠️ 100 secondes CPU/jour (largement suffisant pour comptabilité)
- ⚠️ Accès limité à certaines IPs (peut être un problème si vous êtes au Sénégal)

## Passer au Plan Payant ($5/mois)

Si vous avez besoin:
- D'accès depuis le Sénégal sans restriction
- De plus de CPU
- De support technique

Allez dans **"Account" > "Upgrade"** et choisissez "Hacker plan" ($5/mois)

## Support

- Documentation PythonAnywhere: https://help.pythonanywhere.com
- Forums: https://www.pythonanywhere.com/forums/

Bon déploiement! 🚀
