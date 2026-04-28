import time
import logging
from datetime import datetime

from src.datafeed.fetcher import DataFetcher
from src.engine.indicators import IndicatorEngine
from src.engine.strategy import StrategyEngine
from src.engine.risk_manager import RiskManager
from src.broker.binance_broker import BinanceBroker

logger = logging.getLogger("CassandrePipeline")

class TradingPipeline:
    """
    Chef d'orchestre de Cassandre (T2.4).
    Exécute un cycle complet : Data -> Indicateurs -> Signaux -> Risque -> Broker
    Gère le mode "Trading Live Continu" avec Stop-Loss ultra-réactif.
    """
    def __init__(self, use_broker=True):
        self.data_fetcher = DataFetcher(use_cache=False)
        self.indicator_engine = IndicatorEngine()
        self.strategy_engine = StrategyEngine()
        
        self.broker = None
        self.risk_manager = None
        
        if use_broker:
            self.broker = BinanceBroker()
            try:
                self.broker.connect()
            except Exception as e:
                logger.warning(f"[Pipeline] Broker indisponible : {e} — mode sans broker.")
                self.broker = None
            if self.broker:
                self.risk_manager = RiskManager(broker=self.broker)

        # Suivi de la position
        self.current_position = 0 
        self.entry_price = 0.0
        self.current_sl = 0.0
        self.current_tp = 0.0
        
        # Statut du bot (Boucle asynchrone)
        self.is_running = False

    def run_cycle(self, symbol="BTC-USD", interval="15m", period="7d", fast_check_only=False, max_capital: float = None):
        """
        Exécute 1 boucle d'analyse.
        Si fast_check_only, vérifie uniquement les TP/SL actuels.
        :return: Tuple (Message de log détaillé, le signal principal généré)
        """
        # --- 1. Rapatriement express du prix actuel ---
        # On force "3h" et "1m" pour être dans de la haute fréquence (180 bougies de 1 minute max)
        df_raw = self.data_fetcher.fetch_historical_data(symbol, period="3h", interval="1m", force_refresh=True)
        if df_raw is None or df_raw.empty:
            return "❌ Impossible de récupérer les données.", "ERROR"
            
        current_price = df_raw.iloc[-1]['Close']
        timestamp_str = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp_str}] 🔎 {symbol} @ {current_price:.2f}$"

        # --- 2. GESTION ULTRA-RÉACTIVE DU RISQUE (TP/SL) ---
        if self.current_position == 1 and self.broker and self.risk_manager:
            asset = symbol.replace('-USD', '').replace('USDT', '')
            base_balance = self.broker.get_balance(asset)
            
            # Vérification du Take-Profit (+1.5%)
            if current_price >= self.current_tp:
                profit_usd = (current_price - self.entry_price) * base_balance
                log_msg = f"[{timestamp_str}] 🟢 TAKE-PROFIT TOUCHÉ ! Vente en profit (+{profit_usd:.2f}$)"
                logger.info(log_msg)
                
                if base_balance > 0:
                    self.broker.create_order(symbol, side='sell', order_type='market', amount=base_balance)
                self._reset_position()
                return log_msg, "SELL"
                
            # Vérification du Stop-Loss (-1.0%)
            elif current_price <= self.current_sl:
                loss_usd = (self.entry_price - current_price) * base_balance
                log_msg = f"[{timestamp_str}] 🔴 STOP-LOSS DÉCLENCHÉ ! Arrêt d'urgence de la perte (-{loss_usd:.2f}$)"
                logger.warning(log_msg)
                
                if base_balance > 0:
                    self.broker.create_order(symbol, side='sell', order_type='market', amount=base_balance)
                self._reset_position()
                return log_msg, "SELL"

            if fast_check_only:
                # On est en position, le prix est normal, on patiente.
                return f"[{timestamp_str}] 🧘 Position Ouverte. En attente (SL: {self.current_sl:.1f} | TP: {self.current_tp:.1f}) | Prix: {current_price:.2f}$", "HOLD"

        # --- 3. GESTION STRATÉGIQUE NORMALE (Si pas de fast check) ---
        df_ind = self.indicator_engine.compute_all(df_raw)
        signal_data = self.strategy_engine.generate_signal(df_ind)
        signal = signal_data.get('signal', 'HOLD')
        price = signal_data.get('price', current_price)
        
        if self.broker and self.risk_manager:
            asset = symbol.replace('-USD', '').replace('USDT', '')
            quote_balance = self.broker.get_balance("USDT")
            base_balance = self.broker.get_balance(asset)
            
            if signal == "BUY" and self.current_position == 0:
                # Respecter le plafond de capital alloué si défini
                effective_capital = min(quote_balance, max_capital) if max_capital else quote_balance
                amount_to_buy = self.risk_manager.calculate_position_size(capital=effective_capital, current_price=price)
                if self.risk_manager.is_trade_safe(symbol, 'buy', amount_to_buy, price, quote_balance):
                    sl_price, tp_price = self.risk_manager.calculate_sl_tp_prices('buy', price)
                    
                    order = self.broker.create_order(symbol, side='buy', order_type='market', amount=amount_to_buy)
                    if order:
                        self.current_position = 1
                        self.entry_price = price
                        self.current_sl = sl_price
                        self.current_tp = tp_price
                        log_msg = f"[{timestamp_str}] 🚀 ACHAT {asset} exécuté à {price:.2f}$."
                        return log_msg, "BUY"
                        
            elif signal == "SELL" and self.current_position == 1:
                if base_balance > 0:
                    self.broker.create_order(symbol, side='sell', order_type='market', amount=base_balance)
                self._reset_position()
                log_msg = f"[{timestamp_str}] 📉 VENTE STRATÉGIQUE exécutée à {price:.2f}$."
                return log_msg, "SELL"

        if signal == "HOLD" and self.current_position == 0:
             log_msg = f"[{timestamp_str}] 👁️ Surveillance du marché... Prix: {current_price:.2f}$. Aucun signal."

        return log_msg, signal

    def _reset_position(self):
        self.current_position = 0
        self.entry_price = 0.0
        self.current_sl = 0.0
        self.current_tp = 0.0

    def start_bot(self):
        """Active le flag du bot"""
        self.is_running = True
        logger.info("⚡ Robot ALLUMÉ. Prêt pour le trading live.")

    def stop_bot(self):
        """Désactive le flag du bot"""
        self.is_running = False
        logger.info("🛑 Robot ÉTEINT.")

    def live_trading_loop(self, symbol="BTC-USD"):
        """
        Générateur utilisé par Gradio.
        Tourne en boucle toutes les 15 secondes.
        Retourne le journal de bord (historique textuel) au Dashboard.
        """
        logs = ["=== ⚡ MODE EXPERT SCALPING ACTIVÉ (3s) ===\n"]
        self.start_bot()

        while self.is_running:
            try:
                # 1. On lance le cycle HFT (Intervalle forcé dans la fonction en 1m)
                msg, sig = self.run_cycle(symbol=symbol, period="3h", interval="1m")

                # 2. Ajout au log
                logs.append(msg)

                # Bridage strict des logs pour la propreté de l'interface
                if len(logs) > 8:
                    logs.pop(1)

                display_text = "\n".join(logs)

                # 3. Renvoi à l'interface
                yield display_text

                # 4. Attente active hyper agressive de 3 secondes
                for _ in range(3):
                    if not self.is_running: break
                    time.sleep(1)

            except Exception as e:
                logger.error(f"Erreur dans la boucle Live: {e}")
                logs.append(f"❌ [ERREUR SYSTÈME] {str(e)}")
                yield "\n".join(logs)
                time.sleep(5)

        # Fin de boucle
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 🛑 Bot arrêté par l'utilisateur.")
        yield "\n".join(logs)

    def live_multi_trading_loop(self, symbols: list, capital: float = 100.0):
        """
        Générateur multi-actifs — cycle sur tous les symboles sélectionnés.
        À chaque cycle, analyse un symbole à la fois en rotation.
        :param capital: Capital maximum alloué en USDT pour ce portefeuille de bouquet.
        """
        if not symbols:
            yield "Aucun actif sélectionné."
            return

        n = len(symbols)
        logs = [
            f"=== 🌐 MODE MULTI-ACTIFS — {n} actif(s) ===",
            f"    Capital alloué : {capital:.2f} USDT\n",
        ]
        self.start_bot()

        while self.is_running:
            # Contrôle du capital restant avant chaque cycle
            if self.broker:
                try:
                    available = self.broker.get_balance("USDT")
                    if available < capital * 0.05:  # < 5 % du capital alloué
                        logs.append(
                            f"[{datetime.now().strftime('%H:%M:%S')}]"
                            f" ⛔ Capital épuisé ({available:.2f} USDT). Bot stoppé."
                        )
                        yield "\n".join(logs)
                        self.stop_bot()
                        return
                except Exception:
                    pass

            for symbol in symbols:
                if not self.is_running:
                    break
                try:
                    msg, _ = self.run_cycle(
                        symbol=symbol, period="3h", interval="1m",
                        max_capital=capital / len(symbols),
                    )
                    logs.append(msg)
                    if len(logs) > 18:
                        logs.pop(2)
                    yield "\n".join(logs)
                    for _ in range(2):
                        if not self.is_running:
                            break
                        time.sleep(1)
                except Exception as exc:
                    logger.error(f"[MultiBot] {symbol} : {exc}")
                    logs.append(f"❌ [{symbol}] {exc}")
                    yield "\n".join(logs)
                    time.sleep(3)

            if self.is_running:
                pause_msg = (
                    f"[{datetime.now().strftime('%H:%M:%S')}]"
                    f" ⏱ Cycle terminé — prochain dans 10 s…"
                )
                logs.append(pause_msg)
                if len(logs) > 18:
                    logs.pop(2)
                yield "\n".join(logs)
                for _ in range(10):
                    if not self.is_running:
                        break
                    time.sleep(1)

        logs.append(
            f"[{datetime.now().strftime('%H:%M:%S')}] 🛑 Bot multi-actifs arrêté."
        )
        yield "\n".join(logs)
