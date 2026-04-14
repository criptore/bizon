#!/bin/bash
# ============================================================
#  Bizon — Lanceur Mac (double-clic pour démarrer)
# ============================================================
cd "$(dirname "$0")"

# Cherche le premier Python 3 disponible
for PYTHON in /usr/local/bin/python3 /usr/bin/python3 python3; do
    command -v $PYTHON &>/dev/null && break
done

# Lancement de l'application en arrière-plan sans bloquer
nohup $PYTHON test_app.py >/dev/null 2>&1 &

# Ferme automatiquement la fenêtre du Terminal qui vient de s'ouvrir
osascript -e 'tell application "Terminal" to tell front window to close' &
exit
