import sys
import logging
from src.engine.pipeline import TradingPipeline

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')

# Configure logging pour voir le debug
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_pipeline():
    print("====================================")
    print(" Lancement Test: Pipeline Cassandre ")
    print("====================================")
    
    # Instance le pipeline (Indicateurs et Strategie uniquement, sans Broker)
    pipeline = TradingPipeline(use_broker=False)
    
    # Exécute 1 boucle sur le Bitcoin avec des bougies de 15 minutes
    signal = pipeline.run_cycle(symbol="BTC-USD", interval="15m", period="7d")
    
    print("====================================")
    print(f" Résultat du cycle : SIGNAL {signal}")
    print("====================================")

if __name__ == "__main__":
    test_pipeline()
