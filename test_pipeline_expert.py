import sys
import logging
from src.engine.pipeline import TradingPipeline

# Configure logging pour voir le debug IA
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_pipeline_expert():
    print("==========================================")
    print(" 🔮 TEST EXPERT : Pipeline + IA Cassandre ")
    print("==========================================")
    
    # 1. Initialisation avec IA activée
    pipeline = TradingPipeline(use_broker=False, use_ai=True)
    
    # 2. Entraînement de l'IA (Simulé sur données historisées)
    print("\n🧠 Étape 1 : Entraînement de l'IA...")
    pipeline.train_ai(symbol="BTC-USD")
    
    # 3. Exécution d'un cycle avec filtrage IA
    print("\n🔎 Étape 2 : Analyse d'un cycle avec Intelligence Artificielle...")
    log_msg, signal = pipeline.run_cycle(symbol="BTC-USD", interval="1m", period="3h")
    
    print("\n==========================================")
    print(f" LOG    : {log_msg}")
    print(f" SIGNAL : {signal}")
    print("==========================================")
    
    if pipeline.ai_engine.is_trained:
        print("✅ VERIFICATION : Moteur IA entraîné et actif.")
    else:
        print("❌ VERIFICATION : Échec de l'entraînement IA.")

if __name__ == "__main__":
    test_pipeline_expert()
