import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator
from ta.volatility import BollingerBands

from src.config import config

class IndicatorEngine:
    """
    Moteur de calcul des indicateurs techniques pour Bizon.
    Utilise la librairie 'ta' pour calculer de façon vectorisée (très performante).
    """

    def __init__(self, rsi_window=14, macd_fast=12, macd_slow=26, macd_sign=9, bb_window=20, bb_dev=2, ema_short=50, ema_long=200):
        # Configuration des périodes
        self.rsi_window = rsi_window
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_sign = macd_sign
        self.bb_window = bb_window
        self.bb_dev = bb_dev
        self.ema_short = ema_short
        self.ema_long = ema_long

    def compute_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcule tous les indicateurs techniques (Cassandre Native).
        On ne supprime plus les NaNs pour préserver l'affichage des bougies.
        """
        if df is None or df.empty:
            return df
            
        df_ind = df.copy()

        # --- RSI (ta) ---
        rsi_indicator = RSIIndicator(close=df_ind["Close"], window=self.rsi_window)
        df_ind["RSI"] = rsi_indicator.rsi()

        # --- MACD (ta) ---
        macd_indicator = MACD(close=df_ind["Close"], window_slow=self.macd_slow, window_fast=self.macd_fast, window_sign=self.macd_sign)
        df_ind["MACD"] = macd_indicator.macd()
        df_ind["MACD_Signal"] = macd_indicator.macd_signal()
        df_ind["MACD_Hist"] = macd_indicator.macd_diff()

        # --- Bollinger Bands (ta) ---
        bb_indicator = BollingerBands(close=df_ind["Close"], window=self.bb_window, window_dev=self.bb_dev)
        df_ind["BB_Upper"] = bb_indicator.bollinger_hband()
        df_ind["BB_Lower"] = bb_indicator.bollinger_lband()
        df_ind["BB_Mid"] = bb_indicator.bollinger_mavg()

        # --- EMA (Pandas Native - Plus stable sur 3.14) ---
        df_ind[f"EMA_{self.ema_short}"] = df_ind["Close"].ewm(span=self.ema_short, adjust=False).mean()
        df_ind[f"EMA_{self.ema_long}"] = df_ind["Close"].ewm(span=self.ema_long, adjust=False).mean()

        return df_ind
