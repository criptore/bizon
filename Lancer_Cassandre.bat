@echo off
:: ============================================================
::  Cassandre 🔮 — Lanceur Windows (double-clic pour démarrer)
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
    echo 📦 Creation de l'environnement virtuel...
    python -m venv venv
    call venv\Scripts\activate
    echo 🔄 Installation initiale des dependances...
    pip install --quiet -r requirements.txt
) else (
    call venv\Scripts\activate
)

:: 4. Lancement de l'application (fenêtre console maintenue)
echo 🚀 Lancement de Cassandre...
venv\Scripts\python.exe main.py
pause
