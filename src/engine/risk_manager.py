import logging

logger = logging.getLogger("CassandreRiskManager")

class RiskManager:
    """
    Gestion des risques et sécurité pour les ordres de trading (US-08).
    Calcule le dimensionnement des positions (Position Sizing) et vérifie les conditions de Stop-Loss (SL) et Take-Profit (TP).
    """
    def __init__(self, broker=None):
        self.broker = broker
        # Paramètres par défaut de sécurité (Haute Fiabilité)
        self.max_risk_per_trade_pct = 0.05  # Risque global
        self.default_stop_loss_pct = 0.010   # SL très serré : -1.0%
        self.default_take_profit_pct = 0.015 # TP très sécurisé : +1.5%

    def calculate_position_size(self, capital: float, current_price: float, risk_per_trade: float = None) -> float:
        """
        Calcule la taille de position maximale en fonction du risque acceptable.
        
        :param capital: Capital total disponible (ex: USDT)
        :param current_price: Prix actuel de l'actif
        :param risk_per_trade: % de capital risqué sur ce trade (défaut: 2%)
        :return: Quantité de l'actif à acheter
        """
        risk = risk_per_trade if risk_per_trade is not None else self.max_risk_per_trade_pct
        risk_amount = capital * risk
        
        # Ce calcul est basique : il suppose qu'on perd le `risk_amount` si le stop-loss est touché.
        # En réalité, Position Size = Risk Amount / (Entry Price - Stop Loss Price)
        # Pour une version simplifiée (sans SL défini à l'avance), on limite la taille totale de l'investissement.
        # Allocation agressive (50%) car le Stop-Loss est très serré à 1%
        max_investment = capital * 0.50
        
        quantity = max_investment / current_price
        return quantity

    def calculate_sl_tp_prices(self, side: str, entry_price: float, sl_pct: float = None, tp_pct: float = None):
        """
        Calcule les prix exacts de Stop-Loss et Take-Profit pour un trade.
        """
        sl = sl_pct if sl_pct is not None else self.default_stop_loss_pct
        tp = tp_pct if tp_pct is not None else self.default_take_profit_pct

        if side.lower() == 'buy':
            sl_price = entry_price * (1 - sl)
            tp_price = entry_price * (1 + tp)
        elif side.lower() == 'sell':
            sl_price = entry_price * (1 + sl)
            tp_price = entry_price * (1 - tp)
        else:
            raise ValueError(f"Side non reconnu: {side}")
            
        return sl_price, tp_price

    def is_trade_safe(self, symbol: str, side: str, amount: float, current_price: float, available_balance: float):
        """
        Vérifie si le trade est autorisé selon les règles de gestion des risques.
        A appeler juste avant le Broker.
        """
        # Vérification 1 : Fonds suffisants (avec une marge d'erreur pour les frais)
        cost = amount * current_price
        if side.lower() == 'buy' and cost > available_balance * 0.99:
            logger.warning(f"⚠️ [RiskManager] Fonds insuffisants pour {symbol}: Coût={cost}, Dispo={available_balance}")
            return False
            
        # Log de validation
        logger.info(f"🛡️ [RiskManager] Trade {side} {symbol} validé par la sécurité. Coût estimé: {cost}")
        return True
