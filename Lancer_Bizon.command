#!/bin/bash
# ============================================================
#  Bizon — Lanceur Mac (double-clic pour démarrer)
# ============================================================
cd "$(dirname "$0")"

# --- FORCE LA VERSION STABLE ---
PYTHON_STABLE="/usr/bin/python3"

# 1. Nettoyage et Réinitialisation
if [ -d "venv" ]; then
    echo "♻️  Réinitialisation vers la version stable..."
    rm -rf venv
fi

echo "📦 Création de l'environnement stable (Python 3.9)..."
$PYTHON_STABLE -m venv venv

# 2. Activation et Installation
source venv/bin/activate
export PYTHONIOENCODING=utf-8

echo "🔄 Mise à jour des outils..."
pip install --quiet --upgrade pip setuptools wheel

echo "🛠️  Vérification des dépendances..."
pip install --quiet -r requirements.txt

# 3. Lancement de l'application
echo "🚀 Lancement de Bizon..."
python3 main.py &
disown

# 4. Fermeture propre
sleep 3
osascript -e 'tell application "Terminal" to tell front window to close' &
exit




