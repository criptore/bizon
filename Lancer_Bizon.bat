@echo off
:: ============================================================
::  Bizon — Lanceur Windows (double-clic pour démarrer)
:: ============================================================

:: Vérifie si Python est installé
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ERREUR: Python n'est pas trouve.
    echo Telechargez Python 3 sur https://python.org/downloads
    echo et cochez "Add Python to PATH" lors de l'installation.
    pause
    exit /b
)

:: Lancement sans fenêtre de commande en arrière-plan
start "" pythonw test_app.py
