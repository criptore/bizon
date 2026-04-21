import pandas as pd
import logging
from src.config import config

logger = logging.getLogger("CassandreStrategy")

class StrategyEngine:
    """
    Logique de Scalping Haute Fréquence (Expert).
    Analyse les micro-mouvements (BB + RSI) pour des réactions à la seconde.
    L'agressivité est ajustée selon le profil de trading choisi.
    """
    def __init__(self, profile_name="NORMAL ⚖️"):
        self.profile_name = profile_name
        self._apply_profile(profile_name)
        self.squeeze_threshold = 0.025 # 2.5% de compression (commun à tous les profils)

    def _apply_profile(self, profile_name):
        """Charge les paramètres spécifiques au profil."""
        profile = config.TRADING_PROFILES.get(profile_name, config.TRADING_PROFILES["NORMAL ⚖️"])
        self.rsi_overbought = profile["rsi_overbought"]
        self.rsi_oversold = profile["rsi_oversold"]
        self.ai_confidence_threshold = profile["ai_confidence"]
        logger.info(f"🎯 [Strategy] Profil '{profile_name}' appliqué (RSI: {self.rsi_oversold}/{self.rsi_overbought}, IA Conf: {self.ai_confidence_threshold*100}%)")

    def set_profile(self, profile_name):
        """Change le profil à la volée."""
        self.profile_name = profile_name
        self._apply_profile(profile_name)

    def generate_signal(self, df: pd.DataFrame, ai_engine=None) -> dict:
        """
        Scanne la toute dernière respiration du marché.
        Optionnellement, filtre par l'IA si un moteur est fourni.
        """
        if df is None or df.empty or len(df) < 2:
            return {"signal": "HOLD", "reason": "Not enough data"}

        last_row = df.iloc[-1]
        
        required_cols = ['Close', 'RSI', 'BB_Upper', 'BB_Lower', 'BB_Mid']
        if not all(col in df.columns for col in required_cols):
            return {"signal": "HOLD", "reason": "Missing indicators"}

        current_price = last_row['Close']
        current_rsi = last_row['RSI']
        bb_upper = last_row['BB_Upper']
        bb_lower = last_row['BB_Lower']
        bb_mid = last_row['BB_Mid']

        # Mesure la volatilité (la contraction des bandes)
        band_width = (bb_upper - bb_lower) / bb_mid if bb_mid > 0 else 1.0

        technical_signal = "HOLD"
        reason = f"Volatilité: {band_width*100:.1f}%"

        # === ANALYSE TECHNIQUE (FAIBLE BRUIT) ===
        if current_price < bb_lower and current_rsi < self.rsi_oversold:
            technical_signal = "BUY"
            reason = "BB Rebound (Dip)"
        elif band_width < self.squeeze_threshold and current_price > bb_upper:
            technical_signal = "BUY"
            reason = "Squeeze Breakout"
        elif current_price > bb_upper and current_rsi > self.rsi_overbought:
            technical_signal = "SELL"
            reason = "BB Over-Extension"

        # === FILTRE IA (CONFIRMATION EXPERTE) ===
        if ai_engine and ai_engine.is_trained:
            prob_up, ai_signal = ai_engine.predict(df)
            
            # Cas 1: Confirmation d'achat technique par l'IA (Seuil variable par profil)
            if technical_signal == "BUY":
                if prob_up > self.ai_confidence_threshold:
                    logger.info(f"🔮 [IA] Signal ACHAT Technical validé par l'IA (Confiance: {prob_up*100:.1f}%)")
                else:
                    logger.info(f"🔮 [IA] Signal ACHAT Technical BLOQUÉ par l'IA (Confiance faible: {prob_up*100:.1f}% < {self.ai_confidence_threshold*100}%)")
                    technical_signal = "HOLD"
                    reason = "IA Low Confidence"
            
            # Cas 2: Signal IA pur si très fort (Seuil boosté de 15% par rapport au seuil du profil)
            elif technical_signal == "HOLD" and prob_up > min(0.95, self.ai_confidence_threshold + 0.15):
                technical_signal = "BUY"
                reason = "IA Strong Predictive Buy"
                logger.info(f"🚀 [IA] Signal ACHAT Prédictif Pur (Confiance: {prob_up*100:.1f}%)")

        return {"signal": technical_signal, "reason": reason, "price": current_price}
