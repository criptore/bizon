#!/bin/bash
# ============================================================
#  Bizon — Lanceur Mac (double-clic pour démarrer)
# ============================================================

cd "$(dirname "$0")"

PYTHON=/usr/local/bin/python3

echo "==== Bizon — Vérification de l'environnement ===="

$PYTHON -c "import psutil" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[!] psutil non trouvé — installation en cours..."
    $PYTHON -m pip install --user psutil
    echo "[+] psutil installé."
else
    echo "[+] psutil déjà présent, pas de réinstallation."
fi

echo "==== Lancement de l'application ===="
$PYTHON test_app.py
