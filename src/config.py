import logging
import os
from dotenv import load_dotenv

from src.hardware.detector import detect_hardware

# Charge le fichier .env
load_dotenv()

logger = logging.getLogger("cassandre_config")

class CassandreConfig:
    """
    Singleton de configuration globale de Cassandre.
    S'auto-évalue au premier lancement pour adapter Cassandre au Hardware actuel.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CassandreConfig, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        logger.info("⚡ Initialisation du contexte Hardware Cassandre...")
        self.hw_report = detect_hardware()
        
        # Extraction des paramètres optimisés par le détecteur
        adaptation = self.hw_report.get("adaptation", {})
        
        self.workers = adaptation.get("workers", 1)
        self.batch_size = adaptation.get("batch_size", 16)
        self.calc_frequency_ms = adaptation.get("calc_frequency_ms", 200)
        
        # Contexte matériel pour le dashboard
        cpu_cores = self.hw_report.get("cpu", {}).get("cores_physical", "?")
        gpu_device = self.hw_report.get("gpu", {}).get("device", "CPU")
        
        # Badge pour certifier à l'utilisateur que l'IA détecte correctement son moteur
        self.hardware_badge = f"🚀 Accélération matérielle {gpu_device} active ({cpu_cores} cœurs)"

        # --- Configuration Broker (Binance) ---
        self.binance_api_key = os.getenv("BINANCE_API_KEY", "")
        self.binance_secret_key = os.getenv("BINANCE_SECRET_KEY", "")
        self.binance_testnet = os.getenv("BINANCE_TESTNET", "True").lower() in ("true", "1", "yes")

    # --- PROFILS DE TRADING EXPERTS ---
    # Ces profils ajustent l'agressivité de Cassandre
    TRADING_PROFILES = {
        "FULL SECURE 🛡️": {
            "rsi_oversold": 30,
            "rsi_overbought": 75,
            "sl_pct": 0.008,          # -0.8%
            "tp_pct": 0.012,          # +1.2%
            "ai_confidence": 0.75,    # 75% requis
            "risk_per_trade": 0.05,   # 5% du capital
            "desc": "Sécurité maximale. Très peu de trades, mais haute fiabilité."
        },
        "NORMAL ⚖️": {
            "rsi_oversold": 35,
            "rsi_overbought": 70,
            "sl_pct": 0.010,          # -1.0%
            "tp_pct": 0.015,          # +1.5%
            "ai_confidence": 0.65,    # 65% requis
            "risk_per_trade": 0.10,   # 10% du capital
            "desc": "Mode standard. Équilibre entre risque et opportunités."
        },
        "HYPER DYNAMIQUE 🚀": {
            "rsi_oversold": 40,
            "rsi_overbought": 65,
            "sl_pct": 0.025,          # -2.5%
            "tp_pct": 0.050,          # +5.0%
            "ai_confidence": 0.55,    # 55% requis
            "risk_per_trade": 0.20,   # 20% du capital
            "desc": "Agressif. Profite de la moindre volatilité. Risque élevé."
        }
    }

# Instanciation globale importable par n'importe quel module
config = CassandreConfig()
