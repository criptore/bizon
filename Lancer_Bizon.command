#!/bin/bash
# ============================================================
#  Bizon — Lanceur Mac (double-clic pour démarrer)
# ============================================================
cd "$(dirname "$0")"

# Cherche le premier Python 3 disponible
for PYTHON in /usr/local/bin/python3 /usr/bin/python3 python3; do
    command -v $PYTHON &>/dev/null && break
done

echo "==== Bizon — Lancement avec $PYTHON ===="
$PYTHON test_app.py
