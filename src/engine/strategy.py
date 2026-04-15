import pandas as pd
import logging

logger = logging.getLogger("CassandreStrategy")

class StrategyEngine:
    """
    Logique de Scalping Haute Fréquence (Expert).
    Analyse les micro-mouvements (BB + RSI) pour des réactions à la seconde.
    """
    def __init__(self):
        # Paramètres très sensibles
        self.rsi_overbought = 70
        self.rsi_oversold = 35
        self.squeeze_threshold = 0.025 # 2.5% de compression

    def generate_signal(self, df: pd.DataFrame) -> dict:
        """
        Scanne la toute dernière respiration du marché.
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

        # === LOGIQUE ACHAT (SCALPING PRO) ===
        # 1. Rebond Chirurgical (Le prix sort par le bas et RSI est écrasé)
        if current_price < bb_lower and current_rsi < self.rsi_oversold:
            reason = "BB Rebound (Dip)"
            logger.info(f"⚡ [Expert] Signal ACHAT Rebond détecté: {current_price:.2f}$ (RSI={current_rsi:.1f})")
            return {"signal": "BUY", "reason": reason, "price": current_price}
            
        # 2. Breakout Prédictif (Le ressort était comprimé et explose vers le haut)
        if band_width < self.squeeze_threshold and current_price > bb_upper:
            reason = "Squeeze Breakout"
            logger.info(f"⚡ [Expert] Signal ACHAT Explosion détectée: {current_price:.2f}$")
            return {"signal": "BUY", "reason": reason, "price": current_price}

        # === LOGIQUE VENTE (PRÉ-SÉCURITÉ) ===
        # Remarque : Le vrai Stop-Loss et Take-Profit sont gérés en amont dans le pipeline !
        # Ici c'est uniquement si le TP n'a pas été atteint mais que le marché montre une fatigue extrême.
        if current_price > bb_upper and current_rsi > self.rsi_overbought:
            return {"signal": "SELL", "reason": "BB Over-Extension", "price": current_price}

        return {"signal": "HOLD", "reason": f"Volatilité: {band_width*100:.1f}%", "price": current_price}
