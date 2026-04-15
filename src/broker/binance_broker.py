import ccxt
import logging
from src.config import config

logger = logging.getLogger("CassandreBroker")

class BinanceBroker:
    """
    Gestion des interactions avec l'API Binance (Ordres, Solde, etc.) via CCXT.
    Supporte nativement le Paper Trading via le Testnet de Binance.
    """
    def __init__(self):
        self.api_key = config.binance_api_key
        self.secret_key = config.binance_secret_key
        self.is_testnet = config.binance_testnet
        self.exchange = None

    def connect(self):
        """
        Initialise la connexion à Binance.
        """
        if not self.api_key or not self.secret_key:
            logger.error("❌ [Broker] Clés API Binance manquantes dans le fichier .env.")
            raise ValueError("Les clés API Binance ne sont pas configurées.")

        logger.info(f"🔌 [Broker] Connexion à Binance... (Testnet: {self.is_testnet})")
        
        try:
            self.exchange = ccxt.binance({
                'apiKey': self.api_key,
                'secret': self.secret_key,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot',
                    'adjustForTimeDifference': True,
                }
            })
            
            # Activation du Testnet
            if self.is_testnet:
                self.exchange.set_sandbox_mode(True)
            
            # Test de connexion (charge les marchés et vérifie les permissions)
            self.exchange.load_markets()
            logger.info("✅ [Broker] Connecté avec succès à Binance ! Marchés chargés.")
            return True
            
        except ccxt.AuthenticationError as e:
            logger.error(f"❌ [Broker] Erreur d'authentification Binance : {e}")
            self.exchange = None
            return False
        except Exception as e:
            logger.error(f"❌ [Broker] Impossible de se connecter à Binance : {e}")
            self.exchange = None
            return False

    def get_balance(self, asset="USDT"):
        """
        Récupère le solde disponible pour un actif spécifique (ex: USDT, BTC).
        """
        if not self.exchange:
            logger.warning("⚠️ [Broker] Impossible de récupérer le solde : non connecté.")
            return 0.0
            
        try:
            balance = self.exchange.fetch_balance()
            if asset in balance and 'free' in balance[asset]:
                return balance[asset]['free']
            return 0.0
        except Exception as e:
            logger.error(f"❌ [Broker] Erreur lors de la récupération du solde {asset}: {e}")
            return 0.0

    def create_order(self, symbol, side, order_type="market", amount=None, price=None):
        """
        Passe un ordre d'achat (buy) ou de vente (sell).
        
        :param symbol: ex 'BTC/USDT'
        :param side: 'buy' ou 'sell'
        :param order_type: 'market' ou 'limit'
        :param amount: Quantité (en BTC si symbol=BTC/USDT)
        :param price: Prix unitaire si type='limit'
        """
        if not self.exchange:
            logger.warning("⚠️ [Broker] Impossible de passer un ordre : non connecté.")
            return None
            
        try:
            logger.info(f"🛒 [Broker] Passage d'ordre {order_type.upper()} {side.upper()} sur {symbol} | Qty: {amount} | Price: {price}")
            
            # ccxt utilise le format BTC/USDT (avec le slash)
            formatted_symbol = symbol.replace('-', '/').upper()
            if '/' not in formatted_symbol and len(formatted_symbol) > 3:
                # Fallback simple pour BTCUSDT -> BTC/USDT si manquant
                formatted_symbol = formatted_symbol.replace('USDT', '/USDT')
                
            if order_type.lower() == "market":
                order = self.exchange.create_market_order(formatted_symbol, side, amount)
            elif order_type.lower() == "limit":
                if price is None:
                    raise ValueError("Le prix doit être spécifié pour un ordre Limit.")
                order = self.exchange.create_limit_order(formatted_symbol, side, amount, price)
            else:
                raise ValueError(f"Type d'ordre non supporté: {order_type}")
                
            logger.info(f"✅ [Broker] Ordre exécuté avec succès : {order['id']}")
            return order
            
        except ccxt.InsufficientFunds as e:
            logger.error(f"❌ [Broker] Fonds insuffisants pour cet ordre : {e}")
            return None
        except ccxt.NetworkError as e:
            logger.error(f"❌ [Broker] Erreur réseau lors de l'ordre : {e}")
            return None
        except Exception as e:
            logger.error(f"❌ [Broker] Erreur lors de la création de l'ordre : {e}")
            return None
