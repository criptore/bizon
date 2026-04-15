import sys
import time
from src.engine.pipeline import TradingPipeline

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')

def test_live_loop():
    print("Démarrage du test de la boucle live (Démonstrateur 2 cycles)...")
    pipeline = TradingPipeline(use_broker=True)
    
    # On simule un appel asynchrone sur la boucle
    count = 0
    try:
        for log in pipeline.live_trading_loop(symbol="BTC-USD"):
            print("--- RAPPORT REÇU ---")
            print(log)
            print("--------------------")
            
            count += 1
            if count >= 3:
                print("Arrêt commandé...")
                pipeline.stop_bot()
    except KeyboardInterrupt:
        pipeline.stop_bot()

if __name__ == "__main__":
    test_live_loop()
