#!/bin/bash
# ============================================================
#  Cassandre 🔮 — Lanceur Mac (double-clic pour démarrer)
# ============================================================
cd "$(dirname "$0")"

# --- CHOIX DU PYTHON ---
# Python 3.14 de python.org = pas de Python.app wrapper = subprocess stable sur macOS
# Python 3.9 CommandLineTools = Python.app → subprocess crash SIGABRT (TkpInit) sur macOS Tahoe
if [ -f "/usr/local/bin/python3.14" ]; then
    PYTHON_STABLE="/usr/local/bin/python3.14"
elif [ -f "/usr/local/bin/python3" ]; then
    PYTHON_STABLE="/usr/local/bin/python3"
else
    PYTHON_STABLE="/usr/bin/python3"
fi

# 1. Vérification de l'environnement
if [ ! -d "venv" ]; then
    echo "📦 Création de l'environnement ($($PYTHON_STABLE --version))..."
    $PYTHON_STABLE -m venv venv
    
    echo "🔄 Installation initiale de l'oracle..."
    source venv/bin/activate
    pip install --quiet --upgrade pip
    pip install --quiet -r requirements.txt
    touch venv/.installed
else
    source venv/bin/activate
fi

# 2. Exportation de configuration
export PYTHONIOENCODING=utf-8
export PYTHONUTF8=1

# 3. Lancement de l'application
echo "🚀 Lancement de Cassandre..."
echo "📋 Les logs s'affichent ci-dessous (Ctrl+C pour quitter)..."
echo "---"
python3 main.py




