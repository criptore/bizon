import time
import logging
from datetime import datetime

from src.datafeed.fetcher import DataFetcher
from src.engine.indicators import IndicatorEngine
from src.engine.strategy import StrategyEngine
from src.engine.risk_manager import RiskManager
from src.engine.intelligence import AIEngine
from src.broker.binance_broker import BinanceBroker

logger = logging.getLogger("CassandrePipeline")

class TradingPipeline:
    """
    Chef d'orchestre de Cassandre (T2.4).
    Ajuste son comportement selon le profil de trading choisi (Secure/Normal/Dynamique).
    """
    def __init__(self, use_broker=True, use_ai=True, profile_name="NORMAL ⚖️"):
        self.profile_name = profile_name
        self.data_fetcher = DataFetcher(use_cache=False)
        self.indicator_engine = IndicatorEngine()
        self.strategy_engine = StrategyEngine(profile_name=profile_name)
        self.ai_engine = AIEngine() if use_ai else None
        
        self.broker = None
        self.risk_manager = None
        
        if use_broker:
            self.broker = BinanceBroker()
            self.broker.connect()
            self.risk_manager = RiskManager(broker=self.broker, profile_name=profile_name)

        # Suivi de la position
        self.current_position = 0 
        self.entry_price = 0.0
        self.current_sl = 0.0
        self.current_tp = 0.0
        
        # Statut du bot (Boucle asynchrone)
        self.is_running = False

    def set_profile(self, profile_name):
        """Met à jour le profil de trading pour tous les moteurs."""
        self.profile_name = profile_name
        self.strategy_engine.set_profile(profile_name)
        if self.risk_manager:
            self.risk_manager.set_profile(profile_name)
        logger.info(f"🔄 [Pipeline] Changement vers le profil : {profile_name}")

    def train_ai(self, symbol="BTC-USD"):
        """Entraîne l'IA sur un historique consistant (ex: 7 jours)."""
        if not self.ai_engine:
            return
            
        logger.info(f"🧠 [IA] Chargement de l'historique d'entraînement pour {symbol}...")
        df_train = self.data_fetcher.fetch_historical_data(symbol, period="7d", interval="15m", force_refresh=True)
        if df_train is not None and not df_train.empty:
            df_ind = self.indicator_engine.compute_all(df_train)
            self.ai_engine.train(df_ind)

    def run_cycle(self, symbol="BTC-USD", interval="1m", period="3h", fast_check_only=False):
        """
        Exécute 1 boucle d'analyse en mode temps réel (expert).
        """
        df_raw = self.data_fetcher.fetch_historical_data(symbol, period=period, interval=interval, force_refresh=True)
        if df_raw is None or df_raw.empty:
            return "❌ Erreur données.", "ERROR"
            
        current_price = df_raw.iloc[-1]['Close']
        timestamp_str = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp_str}] 🔎 {symbol} @ {current_price:.2f}$"

        # --- 2. GESTION DU RISQUE (TP/SL RÉALISTES) ---
        if self.current_position == 1 and self.broker and self.risk_manager:
            asset = symbol.replace('-USD', '').replace('USDT', '')
            base_balance = self.broker.get_balance(asset)
            
            # Check Stop-Loss
            if current_price <= self.current_sl:
                log_msg = f"[{timestamp_str}] 🔴 STOP-LOSS ({self.profile_name})"
                if base_balance > 0:
                    self.broker.create_order(symbol, side='sell', order_type='market', amount=base_balance)
                self._reset_position()
                return log_msg, "SELL"
                
            # Check Take-Profit
            elif current_price >= self.current_tp:
                log_msg = f"[{timestamp_str}] 🟢 TAKE-PROFIT ({self.profile_name})"
                if base_balance > 0:
                    self.broker.create_order(symbol, side='sell', order_type='market', amount=base_balance)
                self._reset_position()
                return log_msg, "SELL"

        # --- 3. GESTION STRATÉGIQUE ---
        df_ind = self.indicator_engine.compute_all(df_raw)
        signal_data = self.strategy_engine.generate_signal(df_ind, ai_engine=self.ai_engine)
        signal = signal_data.get('signal', 'HOLD')
        
        if self.broker and self.risk_manager:
            quote_balance = self.broker.get_balance("USDT")
            
            if signal == "BUY" and self.current_position == 0:
                amount_to_buy = self.risk_manager.calculate_position_size(capital=quote_balance, current_price=current_price)
                if self.risk_manager.is_trade_safe(symbol, 'buy', amount_to_buy, current_price, quote_balance):
                    sl_price, tp_price = self.risk_manager.calculate_sl_tp_prices('buy', current_price)
                    order = self.broker.create_order(symbol, side='buy', order_type='market', amount=amount_to_buy)
                    if order:
                        self.current_position = 1
                        self.entry_price = current_price
                        self.current_sl = sl_price
                        self.current_tp = tp_price
                        log_msg = f"[{timestamp_str}] 🚀 ACHAT ({self.profile_name}) | SL: {sl_price:.1f}"
                        return log_msg, "BUY"
                        
            elif signal == "SELL" and self.current_position == 1:
                asset = symbol.replace('-USD', '').replace('USDT', '')
                base_balance = self.broker.get_balance(asset)
                if base_balance > 0:
                    self.broker.create_order(symbol, side='sell', order_type='market', amount=base_balance)
                self._reset_position()
                log_msg = f"[{timestamp_str}] 📉 VENTE STRATÉGIQUE ({self.profile_name})"
                return log_msg, "SELL"

        return log_msg, signal

    def _reset_position(self):
        self.current_position = 0
        self.entry_price = 0.0
        self.current_sl = 0.0
        self.current_tp = 0.0

    def start_bot(self):
        self.is_running = True

    def stop_bot(self):
        self.is_running = False

    def live_trading_loop(self, symbol="BTC-USD"):
        logs = [f"=== ⚡ MODE {self.profile_name} ACTIVÉ ===\n"]
        self.start_bot()
        
        if self.ai_engine and not self.ai_engine.is_trained:
            logs.append("🧠 [IA] Entraînement initial...")
            yield "\n".join(logs)
            self.train_ai(symbol)
            logs.append("✅ [IA] Cerveau opérationnel.")
            yield "\n".join(logs)

        while self.is_running:
            try:
                msg, sig = self.run_cycle(symbol=symbol)
                logs.append(msg)
                if len(logs) > 8: logs.pop(1) 
                yield "\n".join(logs)
                time.sleep(10) # Pause entre cycles
            except Exception as e:
                logger.error(f"Erreur Loop: {e}")
                time.sleep(5)
