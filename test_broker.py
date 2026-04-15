import sys
import logging
from src.broker.binance_broker import BinanceBroker

# Configure logging pour voir les logs du terminal
logging.basicConfig(level=logging.INFO)

def test_binance():
    broker = BinanceBroker()
    connected = broker.connect()
    
    if connected:
        usdt_balance = broker.get_balance("USDT")
        print(f"Solde USDT sur Binance Testnet: {usdt_balance}")
        
        # Test de passage d'un ordre (très petite quantité pour tester si le testnet marche bien)
        # Mais ne testons pas tout de suite sans demander au user si on est bien sur testnet 
        # (on a activé set_sandbox_mode(True), donc on est safe)
    else:
        print("Échec de connexion.")

if __name__ == "__main__":
    test_binance()
