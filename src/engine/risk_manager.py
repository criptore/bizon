import logging
from src.config import config

logger = logging.getLogger("CassandreRiskManager")

class RiskManager:
    """
    Gestion des risques et sécurité pour les ordres de trading (Expert).
    Ajuste automatiquement le Stop-Loss, Take-Profit et la Taille de Position
    selon le profil de trading sélectionné.
    """
    def __init__(self, broker=None, profile_name="NORMAL ⚖️"):
        self.broker = broker
        self.profile_name = profile_name
        self._apply_profile(profile_name)

    def _apply_profile(self, profile_name):
        """Charge les paramètres de risque depuis la config globale."""
        profile = config.TRADING_PROFILES.get(profile_name, config.TRADING_PROFILES["NORMAL ⚖️"])
        self.max_risk_per_trade_pct = profile["risk_per_trade"]
        self.default_stop_loss_pct = profile["sl_pct"]
        self.default_take_profit_pct = profile["tp_pct"]
        logger.info(f"🛡️ [Risk] Profil '{profile_name}' appliqué (Risk: {self.max_risk_per_trade_pct*100}%, SL: -{self.default_stop_loss_pct*100}%, TP: +{self.default_take_profit_pct*100}%)")

    def set_profile(self, profile_name):
        """Change dynamiquement la gestion du risque."""
        self.profile_name = profile_name
        self._apply_profile(profile_name)

    def calculate_position_size(self, capital: float, current_price: float, risk_per_trade: float = None) -> float:
        """
        Calcule la taille de position maximale selon le profil.
        Un profil 'DYNAMIQUE' autorisera une plus grande part de capital par trade.
        """
        risk = risk_per_trade if risk_per_trade is not None else self.max_risk_per_trade_pct
        
        # On limite l'investissement total par trade pour éviter l'all-in catastrophique.
        # Secure: 25% max | Normal: 50% max | Dynamique: 75% max
        limit_ratios = {"FULL SECURE 🛡️": 0.25, "NORMAL ⚖️": 0.50, "HYPER DYNAMIQUE 🚀": 0.75}
        ratio = limit_ratios.get(self.profile_name, 0.50)
        
        max_investment = capital * ratio
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
        """Vérifie si le trade est autorisé selon les fonds disponibles."""
        cost = amount * current_price
        if side.lower() == 'buy' and cost > available_balance * 0.99:
            logger.warning(f"⚠️ [RiskManager] Fonds insuffisants pour {symbol}: Coût={cost}, Dispo={available_balance}")
            return False
        return True
