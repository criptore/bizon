import logging
import sys
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, as_completed

# Forcer UTF-8 sur stdout pour éviter les crashs d'emoji sur Windows (cp1252)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

logger = logging.getLogger("BasketScanner")

# ── Définition des bouquets (6 × 10 = 60 symboles) ────────────────────────────
BASKETS: dict[str, list[str]] = {
    "Crypto — Blue Chips": [
        "BTC-USD", "ETH-USD", "BNB-USD", "SOL-USD", "XRP-USD",
        "ADA-USD", "AVAX-USD", "DOT-USD", "MATIC-USD", "LINK-USD",
    ],
    "Meme Coins": [
        "DOGE-USD", "SHIB-USD", "PEPE-USD", "FLOKI-USD", "WIF-USD",
        "BONK-USD", "MEME-USD", "SATS-USD", "NEIRO-USD", "MOG-USD",
    ],
    "DeFi": [
        "UNI-USD", "AAVE-USD", "CRV-USD", "MKR-USD", "COMP-USD",
        "SNX-USD", "YFI-USD", "BAL-USD", "1INCH-USD", "SUSHI-USD",
    ],
    "Tech Stocks": [
        "AAPL", "MSFT", "NVDA", "GOOGL", "META",
        "AMZN", "AMD", "TSLA", "INTC", "CRM",
    ],
    "ETFs & Indices": [
        "SPY", "QQQ", "DIA", "IWM", "VTI",
        "GLD", "SLV", "USO", "TLT", "XLE",
    ],
    "Forex Majors": [
        "EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCHF=X", "AUDUSD=X",
        "USDCAD=X", "NZDUSD=X", "EURGBP=X", "EURJPY=X", "GBPJPY=X",
    ],
}

BASKET_NAMES: list[str] = list(BASKETS.keys())

_SIGNAL_ORDER = {"BUY": 0, "SELL": 1, "HOLD": 2, "ERREUR": 3}


def _fmt_price(price: float) -> str:
    if price is None:
        return "—"
    if price >= 1000:
        return f"{price:.2f}"
    if price >= 1:
        return f"{price:.4f}"
    if price >= 0.001:
        return f"{price:.6f}"
    return f"{price:.8f}"


def _err(symbol: str, msg: str = "") -> dict:
    return {
        "symbol": symbol,
        "price": None,
        "change": None,
        "signal": "ERREUR",
        "rsi": None,
        "bb_pct": None,
        "reason": msg,
    }


class BasketScanner:
    """Scanne en parallèle tous les symboles d'un bouquet et retourne leurs signaux."""

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers

    def _scan_one(self, symbol: str) -> dict:
        try:
            from src.datafeed.fetcher import DataFetcher
            from src.engine.indicators import IndicatorEngine
            from src.engine.strategy import StrategyEngine

            # use_cache=False évite les conflits SQLite en parallèle
            fetcher = DataFetcher(use_cache=False)
            engine = IndicatorEngine()
            strategy = StrategyEngine()

            df = fetcher.fetch_historical_data(
                symbol, period="5d", interval="1h", force_refresh=True
            )
            if df is None or df.empty:
                return _err(symbol, "Données indisponibles")

            df = engine.compute_all(df)
            sig = strategy.generate_signal(df)

            last = df.iloc[-1]
            price = float(last["Close"])
            prev_price = float(df.iloc[-2]["Close"]) if len(df) >= 2 else price
            change = ((price - prev_price) / prev_price * 100) if prev_price else 0.0

            rsi_raw = last.get("RSI")
            bb_u = float(last.get("BB_Upper", price))
            bb_l = float(last.get("BB_Lower", price))
            bb_pct = (
                ((price - bb_l) / (bb_u - bb_l) * 100) if (bb_u - bb_l) > 0 else 50.0
            )

            return {
                "symbol": symbol,
                "price": price,
                "change": round(change, 2),
                "signal": sig.get("signal", "HOLD"),
                "rsi": round(float(rsi_raw), 1) if rsi_raw is not None else None,
                "bb_pct": round(bb_pct, 1),
                "reason": sig.get("reason", ""),
            }
        except Exception as exc:
            logger.warning(f"[BasketScanner] {symbol} : {exc}")
            return _err(symbol, str(exc)[:60])

    def scan_basket(self, basket_name: str, total_timeout: int = 60) -> list[dict]:
        """Scanne tous les symboles d'un bouquet. Retourne liste triée BUY→SELL→HOLD→ERREUR.

        total_timeout: secondes max pour l'ensemble du scan (défaut 60 s).
        """
        symbols = BASKETS.get(basket_name, [])
        if not symbols:
            return []

        results: list[dict] = []
        executor = ThreadPoolExecutor(max_workers=self.max_workers)
        futures = {executor.submit(self._scan_one, sym): sym for sym in symbols}
        try:
            for future in as_completed(futures, timeout=total_timeout):
                sym = futures[future]
                try:
                    results.append(future.result())
                except Exception as exc:
                    logger.warning(f"[BasketScanner] {sym} : {exc}")
                    results.append(_err(sym, str(exc)[:60]))
        except concurrent.futures.TimeoutError:
            logger.warning("[BasketScanner] Timeout global — certains symboles ignorés.")
            for future, sym in futures.items():
                if not future.done():
                    results.append(_err(sym, "Timeout"))
        finally:
            # Ne pas attendre les threads bloqués sur des appels réseau lents
            executor.shutdown(wait=False, cancel_futures=True)

        results.sort(key=lambda r: _SIGNAL_ORDER.get(r["signal"], 4))
        return results
