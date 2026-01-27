#!/bin/bash
# Script de lancement - CREATES Accounting System

echo "================================================"
echo "  CREATES - Système Comptable GIE"
echo "  Conforme SYSCOHADA"
echo "================================================"
echo ""

cd "$(dirname "$0")"

# Vérifier si les dépendances sont installées
if ! python3 -c "import flask" 2>/dev/null; then
    echo "Installation des dépendances..."
    pip3 install -r requirements.txt
fi

echo "Démarrage du serveur..."
echo ""
echo "Ouvrez votre navigateur à l'adresse:"
echo "  http://localhost:5000"
echo ""
echo "Appuyez sur Ctrl+C pour arrêter le serveur"
echo ""

python3 app.py
