# =====================================================================
# PythonAnywhere WSGI Configuration File
# =====================================================================
# Instructions:
# 1. Uploadez tous les fichiers de l'application sur PythonAnywhere
# 2. Dans l'onglet "Web", créez une nouvelle application Flask
# 3. Remplacez le contenu du fichier WSGI par ce fichier
# 4. Ajustez le chemin ci-dessous selon votre username PythonAnywhere
# =====================================================================

import sys
import os

# IMPORTANT: Remplacez 'votreusername' par votre nom d'utilisateur PythonAnywhere
username = 'votreusername'
project_folder = f'/home/{username}/ngo-accounting'

# Ajouter le dossier du projet au path Python
if project_folder not in sys.path:
    sys.path.insert(0, project_folder)

# Configurer les variables d'environnement
os.environ['FLASK_ENV'] = 'production'
os.environ['SECRET_KEY'] = 'CHANGEZ_CE_SECRET_EN_PRODUCTION_123456789'

# Importer l'application Flask
from app import app as application

# Pour le debugging (à désactiver en production)
# application.config['DEBUG'] = False
