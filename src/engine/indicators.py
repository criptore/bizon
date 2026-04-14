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

    def compute_all(self, df: pd.DataFrame, dropna: bool = True) -> pd.DataFrame:
        """
        Calcule tous les indicateurs techniques et les ajoute au DataFrame.
        """
        if df is None or df.empty:
            return df
            
        # Préparation du moteur pour les algos futurs basés sur la mémoire locale
        batch_size_alloue = config.batch_size
            
        # Création d'une copie pour éviter le warning SettingWithCopy
        df_ind = df.copy()

        # On vérifie si la colonne "Close" existe (absolument nécessaire pour les calculs)
        if "Close" not in df_ind.columns:
            raise KeyError("Le DataFrame doit contenir une colonne 'Close'")

        close_series = df_ind["Close"]

        # --- RSI ---
        rsi_indicator = RSIIndicator(close=close_series, window=self.rsi_window)
        df_ind["RSI"] = rsi_indicator.rsi()

        # --- MACD ---
        macd_indicator = MACD(close=close_series, window_slow=self.macd_slow, window_fast=self.macd_fast, window_sign=self.macd_sign)
        df_ind["MACD"] = macd_indicator.macd()
        df_ind["MACD_Signal"] = macd_indicator.macd_signal()
        df_ind["MACD_Hist"] = macd_indicator.macd_diff()

        # --- Bollinger Bands ---
        bb_indicator = BollingerBands(close=close_series, window=self.bb_window, window_dev=self.bb_dev)
        df_ind["BB_Upper"] = bb_indicator.bollinger_hband()
        df_ind["BB_Lower"] = bb_indicator.bollinger_lband()
        df_ind["BB_Mid"] = bb_indicator.bollinger_mavg() # Simple moving average 20

        # --- EMA ---
        ema_short_indicator = EMAIndicator(close=close_series, window=self.ema_short)
        df_ind[f"EMA_{self.ema_short}"] = ema_short_indicator.ema_indicator()
        
        ema_long_indicator = EMAIndicator(close=close_series, window=self.ema_long)
        df_ind[f"EMA_{self.ema_long}"] = ema_long_indicator.ema_indicator()

        # --- Nettoyage ---
        if dropna:
            # Enlève les lignes au début qui n'ont pas pu calculer d'EMA ou RSI par manque de recul
            df_ind.dropna(inplace=True)

        return df_ind
