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
        # Testnet par défaut si non précisé explicitement à False
        self.binance_testnet = os.getenv("BINANCE_TESTNET", "True").lower() in ("true", "1", "yes")

# Instanciation globale importable par n'importe quel module
config = CassandreConfig()
