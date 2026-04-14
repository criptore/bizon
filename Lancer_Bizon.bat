@echo off
:: ============================================================
::  Bizon — Lanceur Windows (double-clic pour démarrer)
:: ============================================================
setlocal
cd /d "%~dp0"

:: 1. Vérifie Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERREUR: Python est introuvable.
    pause
    exit /b
)

:: 2. Vérifie et active le venv
if not exist "venv" (
    echo 📦 Création de l'environnement virtuel...
    python -m venv venv
)

call venv\Scripts\activate

:: 3. Installe/Met à jour les dépendances
echo 🛠️ Verification des dependances...
pip install --quiet -r requirements.txt

:: 4. Lancement de l'application (sans fenêtre console persistante)
echo 🚀 Lancement de Bizon...
start "" pythonw main.py

exit
