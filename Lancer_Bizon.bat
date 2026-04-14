@echo off
:: ============================================================
::  Bizon — Lanceur Windows (double-clic pour démarrer)
::  Python doit être installé avec "Add to PATH" coché
:: ============================================================
echo ==== Bizon - Lancement ====
python test_app.py
if %errorlevel% neq 0 (
    echo.
    echo ERREUR: Python n'est pas trouve.
    echo Telechargez Python sur https://python.org/downloads
    echo et cochez "Add Python to PATH" lors de l'installation.
    pause
)
