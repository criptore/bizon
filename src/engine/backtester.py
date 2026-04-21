import pandas as pd
import numpy as np
import logging
from src.engine.strategy import StrategyEngine
from src.engine.indicators import IndicatorEngine
from src.engine.intelligence import AIEngine
from src.engine.risk_manager import RiskManager
from src.config import config

logger = logging.getLogger("CassandreBacktester")

class Backtester:
    """
    Simule la stratégie de Cassandre sur des données historiques (Expert).
    Prend désormais en compte les profils de trading (Secure, Normal, Dynamique).
    """
    def __init__(self, initial_capital=10000.0, use_ai=True, profile_name="NORMAL ⚖️"):
        self.initial_capital = initial_capital
        self.strategy = StrategyEngine(profile_name=profile_name)
        self.risk_manager = RiskManager(profile_name=profile_name)
        self.indicator = IndicatorEngine()
        self.ai = AIEngine() if use_ai else None
        self.profile_name = profile_name

    def run(self, df_raw: pd.DataFrame) -> dict:
        """
        Exécute le backtest sur les données brutes selon le profil choisi.
        """
        if df_raw is None or len(df_raw) < 150:
            return {"error": "Historique trop court pour le backtest expert (min 150 bougies)."}
            
        logger.info(f"⏳ [Backtest] Précalcul ({len(df_raw)} bougies) | Profil: {self.profile_name}")
        df_ind = self.indicator.compute_all(df_raw)
        df_ind = df_ind.dropna()
        
        if df_ind.empty:
            return {"error": "Historique trop court après calcul technique."}

        # PHASE D'ENTRAÎNEMENT IA
        if self.ai:
            self.ai.train(df_ind)

        capital = self.initial_capital
        position_size = 0.0
        entry_price = 0.0
        
        trades = []
        equity_history = [self.initial_capital]
        win_trades = 0
        loss_trades = 0

        for i in range(1, len(df_ind)):
            current_slice = df_ind.iloc[i-1:i+1]
            signal_data = self.strategy.generate_signal(current_slice, ai_engine=self.ai)
            signal = signal_data.get('signal', 'HOLD')
            current_price = signal_data.get('price', df_ind.iloc[i]['Close'])
            date = df_ind.index[i]
            
            # Gestion simplifiée du Stop-Loss / Take-Profit pour le backtest
            if position_size > 0:
                pnl_pct = (current_price - entry_price) / entry_price
                
                # Check SL/TP du profil
                if pnl_pct <= -self.risk_manager.default_stop_loss_pct or pnl_pct >= self.risk_manager.default_take_profit_pct:
                    signal = "SELL"
                    reason_exit = "SL Hit" if pnl_pct < 0 else "TP Hit"
                
            if signal == "BUY" and position_size == 0:
                # Utilise le RiskManager pour définir la taille
                position_size = self.risk_manager.calculate_position_size(capital, current_price)
                investment = position_size * current_price
                capital -= investment
                entry_price = current_price
                trades.append({"date": date, "type": "BUY", "price": current_price, "amount": position_size, "reason": signal_data.get("reason", "Technical")})
                
            elif signal == "SELL" and position_size > 0:
                gain = position_size * current_price
                capital += gain
                profit_pct = (current_price - entry_price) / entry_price * 100
                if profit_pct > 0: win_trades += 1
                else: loss_trades += 1
                trades.append({"date": date, "type": "SELL", "price": current_price, "profit_pct": profit_pct, "capital_after": capital})
                position_size = 0.0
                entry_price = 0.0
            
            current_equity = capital + (position_size * current_price)
            equity_history.append(current_equity)

        # Fermeture finale
        if position_size > 0:
            capital += position_size * df_ind.iloc[-1]['Close']
            equity_history[-1] = capital

        # MÉTRIQUES
        history_series = pd.Series(equity_history)
        roll_max = history_series.cummax()
        drawdowns = (history_series - roll_max) / roll_max
        max_drawdown_pct = abs(drawdowns.min() * 100)
        
        returns = history_series.pct_change().dropna()
        sharpe = (returns.mean() / returns.std() * np.sqrt(252)) if (len(returns) > 1 and returns.std() != 0) else 0.0

        total_trades = win_trades + loss_trades
        roi_pct = ((capital - self.initial_capital) / self.initial_capital) * 100
        
        return {
            "initial_capital": self.initial_capital,
            "final_capital": capital,
            "roi_pct": roi_pct,
            "total_trades": total_trades,
            "win_rate": (win_trades / total_trades * 100) if total_trades > 0 else 0.0,
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown_pct": round(max_drawdown_pct, 2),
            "ai_status": "Active" if self.ai and self.ai.is_trained else "Inactive",
            "profile": self.profile_name
        }
