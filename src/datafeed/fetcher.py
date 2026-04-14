import yfinance as yf
import pandas as pd
from typing import Optional
import time

from src.config import config
from .cache import SQLiteCache

class DataFetcher:
    """
    Module pour récupérer les données de marché avec yfinance 
    et utiliser le cache local (SQLite) transparentement.
    """
    def __init__(self, use_cache: bool = True):
        self.use_cache = use_cache
        self.cache = SQLiteCache()

    def fetch_historical_data(self, ticker: str, period: str = "1mo", interval: str = "1d", force_refresh: bool = False) -> Optional[pd.DataFrame]:
        """
        Récupère l'historique des prix. 
        Cherche d'abord dans le cache, sinon télécharge via yfinance.
        """
        start_time = time.time()
        
        # 1. Vérification du cache SQLite
        if self.use_cache and not force_refresh:
            cached_df = self.cache.load(ticker, interval)
            # Pour ce prototype (MVP), si le cache existe, on l'utilise
            if cached_df is not None and not cached_df.empty:
                elapsed = round((time.time() - start_time) * 1000)
                print(f"📦 [DataFeed] {ticker} ({interval}) chargé depuis le cache SQLite ({elapsed}ms)")
                return cached_df
                
        # 2. Téléchargement depuis l'API yfinance
        print(f"🌐 [DataFeed] Téléchargement de {ticker} ({period}, {interval}) via yfinance...")
        try:
            # L'API yfinance gère les pool HTTP si 'threads=True' (quand workers > 1)
            use_threads = True if config.workers > 1 else False
            df = yf.download(tickers=ticker, period=period, interval=interval, progress=False, threads=use_threads)
            
            if df is None or df.empty:
                print(f"❌ [DataFeed] Aucune donnée trouvée pour {ticker}")
                return None
                
            # Les versions récentes de yfinance renvoient parfois un MultiIndex sur les colonnes. 
            # On aplani les colonnes pour simplifier l'utilisation
            if isinstance(df.columns, pd.MultiIndex):
                # Extraire le premier niveau ex: 'Close', 'Open', etc...
                df.columns = df.columns.get_level_values(0)
            
            # Normalisation (S'assurer que l'index s'appelle Date pour notre SQLite et pandas-ta)
            if df.index.name != "Date" and df.index.name != "Datetime":
                df.index.name = "Date"
                
            # 3. Sauvegarde dans le cache
            if self.use_cache:
                self.cache.save(df, ticker, interval)
                
            elapsed = round((time.time() - start_time) * 1000)
            print(f"✅ [DataFeed] {ticker} téléchargé et mis en cache proprement ({elapsed}ms)")
            return df
            
        except Exception as e:
            print(f"❌ [DataFeed] Erreur yfinance pour {ticker}: {e}")
            return None
