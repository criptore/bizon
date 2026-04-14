@echo off
:: ============================================================
::  Cassandre 🔮 — Lanceur Windows (Auto-détection Python)
:: ============================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

:: Force l'encodage UTF-8 pour Windows (emojis, types de caractères)
set PYTHONUTF8=1
chcp 65001 >nul

echo 🔍 Recherche d'une version de Python compatible (3.10+ recommandee)...

:: 1. Détection du meilleur exécutable Python
set "PYTHON_EXE="

:: Test 1: Lanceur 'py' avec version 3.12 (celle que nous avons trouvée)
py -3.12 --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PYTHON_EXE=py -3.12"
    goto :PYTHON_FOUND
)

:: Test 2: Lanceur 'py' générique
py -3 --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PYTHON_EXE=py -3"
    goto :PYTHON_FOUND
)

:: Test 3: 'python' standard
python --version >nul 2>&1
if !errorlevel! equ 0 (
    :: Vérification rapide de la version de 'python'
    for /f "tokens=2" %%v in ('python --version') do set "VER=%%v"
    for /f "tokens=1,2 delims=." %%a in ("!VER!") do (
        if %%a lss 3 (
            echo Python 2 detecte, ignore.
        ) else if %%b lss 8 (
            echo Python !VER! detecte (trop ancien pour Cassandre^).
        ) else (
            set "PYTHON_EXE=python"
            goto :PYTHON_FOUND
        )
    )
)

:PYTHON_NOT_FOUND
echo.
echo ❌ ERREUR: Aucune version compatible de Python n'a ete trouvee.
echo Cassandre nécessite Python 3.8 ou superieur (3.12 recommandé).
echo.
echo Veuillez installer Python depuis https://www.python.org/
echo et assurez-vous de cocher "Add Python to PATH".
pause
exit /b

:PYTHON_FOUND
echo ✅ Utilisation de : !PYTHON_EXE!

:: 2. Gestion de l'environnement virtuel
if not exist "venv" (
    echo 📦 Creation de l'environnement virtuel...
    !PYTHON_EXE! -m venv venv
    if !errorlevel! neq 0 (
        echo ❌ Erreur lors de la creation du venv.
        pause
        exit /b
    )
)

:: 3. Activation et vérification de la version du venv
call venv\Scripts\activate
for /f "tokens=2" %%v in ('python --version') do set "VENV_VER=%%v"
for /f "tokens=1,2 delims=." %%a in ("!VENV_VER!") do (
    if %%b lss 8 (
        echo ⚠️ L'environnement virtuel actuel est en version !VENV_VER! (trop ancienne^).
        echo 🔄 Tentative de réinitialisation...
        deactivate >nul 2>&1
        rmdir /s /q venv >nul 2>&1
        if exist "venv" (
            echo ❌ Impossible de supprimer le dossier 'venv'. Veuillez le supprimer manuellement.
            pause
            exit /b
        )
        echo 📦 Re-creation de l'environnement...
        !PYTHON_EXE! -m venv venv
        call venv\Scripts\activate
    )
)

:: 4. Installation des dépendances
if not exist "venv\.installed" (
    echo 🔄 Mise a jour de pip...
    python -m pip install --quiet --upgrade pip
    
    echo 🔄 Installation des dependances (cela peut prendre une minute^)...
    pip install -r requirements.txt
    if !errorlevel! equ 0 (
        echo. > venv\.installed
    ) else (
        echo.
        echo ❌ ERREUR: L'installation des dependances a echoue.
        echo Cela arrive souvent si Python est trop ancien ou si des outils de compilation manquent.
        pause
        exit /b
    )
)

:: 5. Lancement de l'application
echo.
echo 🚀 Lancement de Cassandre...
python main.py
if !errorlevel! neq 0 (
    echo.
    echo ⚠️ Cassandre s'est arrete avec une erreur.
    pause
)
