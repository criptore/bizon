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

    def _fetch_from_binance(self, ticker: str, interval: str = "1d", period: str = "1y") -> Optional[pd.DataFrame]:
        """
        Récupère les données depuis l'API publique de Binance (Cassandre)
        Avec mécanisme de Retry (3 tentatives) et buffer étendu pour EMA 200.
        """
        import requests
        
        # Mapping ticker: BTC-USD -> BTCUSDT
        symbol = ticker.replace("-USD", "USDT").replace("-", "").upper()
        
        # Mapping interval: 1d -> 1d, 1wk -> 1w
        binance_interval = interval
        if interval == "1wk": binance_interval = "1w"
        elif interval == "1mo": binance_interval = "1M"
        
        # Calcul de la limite nécessaire (Période demandée + Buffer pour indicateurs)
        # EMA 200 a besoin de stabiliser (Warmup). On prend un buffer de 750 bars (3.75x) 
        # pour une précision quasi-parfaite sur l'EMA 200.
        base_limit = 365
        if period == "3mo": base_limit = 90
        elif period == "6mo": base_limit = 180
        elif period == "2y": base_limit = 730
        elif period == "5y": base_limit = 1000 # Capé par l'API Binance
        
        limit = base_limit + 750 # Buffer étendu pour stabilisation EMA 200
        if limit > 1500: limit = 1500 # Extension limite maximale sécurisée API
        
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={binance_interval}&limit={limit}"
        
        for attempt in range(3):
            try:
                if attempt > 0:
                    time.sleep(1.5 * attempt) # Backoff simple

                print(f"📡 [DEBUG] Appel API Binance: {url}")
                response = requests.get(url, timeout=10)
                print(f"📡 [DEBUG] Status HTTP: {response.status_code}")
                response.raise_for_status()
                data = response.json()
                print(f"📡 [DEBUG] Nombre de klines reçues: {len(data)}")
                
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
                
                print(f"✅ [DataFeed] Binance a renvoyé {len(df)} bougies valides pour {symbol}.")
                return df[cols_to_fix]
                
            except Exception as e:
                if attempt == 2: # Dernier essai
                    print(f"⚠️ [DataFeed] Échec définitif Binance pour {ticker} après 3 essais: {e}")
                else:
                    print(f"🔄 [DataFeed] Tentative {attempt+1} échouée pour {ticker}, nouvel essai...")
        
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
            print(f"🌐 [DataFeed] Tentative de récupération via Binance (Public API)...")
            df = self._fetch_from_binance(ticker, interval, period)
            if df is not None and not df.empty:
                if self.use_cache: self.cache.save(df, ticker, interval)
                return df

        # 3. Fallback yfinance
        print(f"🌐 [DataFeed] Téléchargement via yfinance (Fallback)...")
        try:
            import requests
            session = requests.Session()
            session.headers.update({'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'})
            
            use_threads = True if config.workers > 1 else False
            df = yf.download(tickers=ticker, period=period, interval=interval, progress=False, threads=use_threads, session=session)
            
            if df is not None and not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                if df.index.name not in ["Date", "Datetime"]:
                    df.index.name = "Date"
                if self.use_cache: self.cache.save(df, ticker, interval)
                return df
                
        except Exception as e:
            print(f"❌ [DataFeed] Erreur yfinance pour {ticker}: {e}")
            
        return None
