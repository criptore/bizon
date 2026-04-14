# 🦬 Projet Bizon

Bienvenue dans le projet Bizon, le module de trading algorithmique et d'analyse de données intégré au **Projet Olympe**.

Ce projet a pour objectif de fournir un bot de trading complet, allant du backtesting sur des données historiques jusqu'au *paper trading* (mode test) et à l'exécution en mode réel, tout en mettant l'accent sur les performances, la stricte gestion des risques et la compatibilité en local grâce à son module de détection matérielle intelligent.

## 🌟 Fonctionnalités Principales

- **🔍 Détecteur Matériel (Hardware Detector) :** Évaluation des capacités du système (CPU, RAM, GPU, support CUDA/MPS) pour adapter la charge de calcul. Interface graphique premium et multi-plateforme.
- **📊 Flux de Données (DataFeed) :** Récupération de données d'historique via `yfinance` avec un système de cache local SQLite.
- **📈 Moteur d'Indicateurs :** Calcul rapide et en temps réel des indicateurs techniques (RSI, MACD, Bandes de Bollinger, EMA) via `pandas-ta`.
- **💼 Paper Trading et Mode Réel :** Connexion aux API de courtiers (Alpaca, Binance) pour l'exécution des ordres avec protection stricte en mode réel (double confirmation, circuit breaker, et stop-loss automatisé).
- **🛡️ Gestion de Risques (Risk Manager) :** Outils de sécurité intégrés pour préserver le capital, incluant la gestion d'un drawdown maximum de sécurité.
- **💻 Interface Utilisateur Dynamique :** Dashboard web via `Gradio` et `Plotly` offrant le suivi des stratégies, ainsi qu'un exécutable `Tkinter` (avec un rendu arrondi) pour la gestion du système.
- **📋 Backtesting :** Évaluation des stratégies sur données historiques générant des rapports détaillés (Win Rate, P&L, Drawdown).

## 🛠️ Stack Technique

- **Langage / Environnement :** Python
- **Interface / Visualisation :** Gradio, Plotly, Tkinter (UI Canvas customisé)
- **Analyse & Machine Learning (Bonus) :** pandas, pandas-ta, sklearn (Random Forest), PyTorch (LSTM)
- **Finance & Marchés :** yfinance, API Alpaca
- **Infrastructure :** SQLite, pip, Makefile, scripts shell batch/command compatibles multi-OS (Windows, macOS Linux).

## 🚀 Installation & Utilisation Rapide

Pour configurer le projet localement en un temps record (< 15 minutes) tout en respectant les consignes de sécurité obligatoires concernant vos clés API. 

1. **Cloner le dépôt :**
   ```bash
   git clone https://github.com/criptore/bizon.git
   cd bizon
   ```

2. **Créer et activer l'environnement virtuel :**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Sur macOS/Linux
   # Sur Windows: venv\Scripts\activate
   ```

3. **Installer les dépendances :**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configuration (Environnement de sécurité) :**
   Créez votre fichier de configuration local à partir de l'exemple :
   ```bash
   cp .env.example .env
   ```
   > ⚠️ **Sécurité :** Ne mettez **JAMAIS** vos véritables clés API sur Git. Renseignez-les _uniquement_ dans le fichier `.env`. Le mode par défaut est `BIZON_MODE=paper` afin d'éviter tout perte financière de test.

5. **Lancer le détecteur de matériel :**
   Testez les capacités de votre ordinateur avant le premier trade :
   ```bash
   python src/hardware/detector.py
   # Vous pouvez aussi utiliser directement les lanceurs fournis: Lancer_Bizon.bat (Windows) ou Lancer_Bizon.command (macOS)
   ```

## 📈 Lancer l'Application Dashboard

Si toutes les dépendances sont installées et les clés API fonctionnelles, vous pouvez démarrer l'expérience web Gradio :
```bash
make run
```
Le tableau de bord (Dashboard) s'ouvrira automatiquement, généralement sur l'adresse `http://localhost:8501`.

## 🧑‍💻 Architecture, Performances et Continuité

Ce module est développé pour le Projet Olympe (2025–2026).
- **Performances ciblées :** Latence totale de signal à ordre < 500ms en mode Réel, et un recalcul des indicateurs < 100ms par bougie.
- **Développements post-MVP  :** Intégration du module à l'assistant global "Projet Olympe" via commandes vocales ("Olympe, lance Bizon sur BTC en mode test 15 minutes"), ainsi qu'une approche portfolio avec stratégies basées sur modèles LSTM.

---
*Ce README et le projet dans son ensemble sont développés sous contraintes et validation des spécifications du Cahier des Charges Bizon v1.0.*
