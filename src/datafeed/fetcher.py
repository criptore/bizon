import logging
import yfinance as yf
import pandas as pd
from typing import Optional
import time

from src.config import config
from .cache import SQLiteCache

logger = logging.getLogger("CassandreDataFetcher")


class DataFetcher:
    """
    Module pour récupérer les données de marché avec yfinance 
    et utiliser le cache local (SQLite) transparentement.
    """
    def __init__(self, use_cache: bool = True):
        self.use_cache = use_cache
        self.cache = SQLiteCache()

    def _fetch_from_binance(self, ticker: str, interval: str = "1d", period: str = "1y") -> Optional[pd.DataFrame]:
        """
        Récupère les données depuis l'API publique de Binance (Cassandre)
        """
        try:
            import requests
            # Mapping ticker: BTC-USD -> BTCUSDT
            symbol = ticker.replace("-USD", "USDT").replace("-", "").upper()
            
            # Mapping interval: 1d -> 1d, 1wk -> 1w
            binance_interval = interval
            if interval == "1wk": binance_interval = "1w"
            elif interval == "1mo": binance_interval = "1M"
            
            # Calcul de la limite nécessaire (Période demandée + Buffer pour indicateurs)
            # EMA 200 a besoin de 200 points de recul minimum
            base_limit = 365
            if period == "3mo": base_limit = 90
            elif period == "6mo": base_limit = 180
            elif period == "2y": base_limit = 730
            elif period == "5y": base_limit = 1825
            
            limit = base_limit + 300 # Buffer de sécurité de 300 bars
            if limit > 1500: limit = 1500 # Extension limite maximale API
            
            url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={binance_interval}&limit={limit}"
            logger.debug("[DataFeed] Appel API Binance : %s", url)
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Format Binance: [OpenTime, Open, High, Low, Close, Volume, CloseTime, ...]
            df = pd.DataFrame(data, columns=[
                'OpenTime', 'Open', 'High', 'Low', 'Close', 'Volume', 
                'CloseTime', 'QuoteAssetVolume', 'NumTrades', 
                'TakerBuyBaseAssetVolume', 'TakerBuyQuoteAssetVolume', 'Ignore'
            ])
            
            # Conversion stricte des types (OpenTime doit être int avant to_datetime)
            df['OpenTime'] = pd.to_numeric(df['OpenTime'])
            df['Date'] = pd.to_datetime(df['OpenTime'], unit='ms')
            df.set_index('Date', inplace=True)
            
            cols_to_fix = ['Open', 'High', 'Low', 'Close', 'Volume']
            for col in cols_to_fix:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Nettoyage : On enlève les NaNs et les valeurs à 0 qui cassent l'échelle du graphique
            df = df.dropna(subset=cols_to_fix)
            df = df[(df[cols_to_fix] > 0).all(axis=1)]
            
            return df[cols_to_fix]
            
        except Exception as e:
            logger.debug("[DataFeed] Echec Binance pour %s: %s", ticker, e)
            return None

    def fetch_historical_data(self, ticker: str, period: str = "1y", interval: str = "1d", force_refresh: bool = False) -> Optional[pd.DataFrame]:
        """
        Récupère l'historique des prix. 
        Tente Binance pour la crypto, sinon yfinance.
        """
        start_time = time.time()
        
        # 1. Vérification du cache
        if self.use_cache and not force_refresh:
            cached_df = self.cache.load(ticker, interval)
            if cached_df is not None and not cached_df.empty:
                return cached_df
                
        # 2. Tentative Binance si Crypto
        if "-USD" in ticker.upper() or ticker.upper() in ["BTC", "ETH", "SOL"]:
            logger.debug("[DataFeed] Tentative Binance pour %s", ticker)
            df = self._fetch_from_binance(ticker, interval, period)
            if df is not None and not df.empty:
                if self.use_cache: self.cache.save(df, ticker, interval)
                return df

        # 3. Fallback yfinance (1.3.0+ — gère sa propre session curl_cffi)
        logger.debug("[DataFeed] Fallback yfinance pour %s", ticker)
        try:
            # yfinance n'accepte pas les périodes sub-jour ("3h", "6h"…) — on mappe vers "1d"
            _yf_valid = {"1d","5d","1mo","3mo","6mo","1y","2y","5y","10y","ytd","max"}
            yf_period = period if period in _yf_valid else "1d"
            df = yf.download(tickers=ticker, period=yf_period, interval=interval,
                             progress=False, auto_adjust=True)

            if df is not None and not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                df.index.name = "Date"
                if self.use_cache: self.cache.save(df, ticker, interval)
                return df

        except Exception as e:
            logger.warning("[DataFeed] Erreur yfinance pour %s: %s", ticker, e)
            
        return None
