#!/bin/bash

echo "=========================================="
echo "Préparation pour Déploiement PythonAnywhere"
echo "=========================================="
echo ""

# Vérifier que les fichiers essentiels existent
echo "✓ Vérification des fichiers..."
files=("app.py" "requirements.txt" "pythonanywhere_wsgi.py")
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file"
    else
        echo "  ✗ $file MANQUANT!"
        exit 1
    fi
done
echo ""

# Vérifier le dossier templates
if [ -d "templates" ]; then
    count=$(find templates -name "*.html" | wc -l)
    echo "✓ Dossier templates/ : $count fichiers HTML"
else
    echo "✗ Dossier templates/ manquant!"
    exit 1
fi
echo ""

# Créer un fichier .gitignore si absent
if [ ! -f ".gitignore" ]; then
    echo "Création de .gitignore..."
    cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
venv/
env/
ENV/

# Flask
instance/
.webassets-cache

# Base de données locale
*.db

# Uploads (pièces justificatives)
uploads/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
EOF
    echo "✓ .gitignore créé"
else
    echo "✓ .gitignore existe"
fi
echo ""

# Afficher les prochaines étapes
echo "=========================================="
echo "Prochaines étapes:"
echo "=========================================="
echo ""
echo "1. Créez un compte sur https://www.pythonanywhere.com"
echo ""
echo "2. Si vous utilisez Git:"
echo "   git init"
echo "   git add ."
echo "   git commit -m 'Initial commit'"
echo "   git remote add origin VOTRE_REPO_URL"
echo "   git push -u origin master"
echo ""
echo "3. Suivez le guide complet dans:"
echo "   📄 DEPLOIEMENT_PYTHONANYWHERE.md"
echo ""
echo "=========================================="
echo "Fichiers prêts pour le déploiement! ✓"
echo "=========================================="
