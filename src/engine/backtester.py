import pandas as pd
import logging
from src.engine.strategy import StrategyEngine
from src.engine.indicators import IndicatorEngine

logger = logging.getLogger("CassandreBacktester")

class Backtester:
    """
    Simule la stratégie de Cassandre sur des données historiques (US09).
    Traite la donnée ligne par ligne pour mimer les conditions réelles sans look-ahead bias.
    """
    def __init__(self, initial_capital=10000.0):
        self.initial_capital = initial_capital
        self.strategy = StrategyEngine()
        self.indicator = IndicatorEngine()

    def run(self, df_raw: pd.DataFrame, risk_per_trade: float = 0.10) -> dict:
        """
        Exécute le backtest sur les données brutes.
        Retourne les statistiques globales (P&L, nombre de trades).
        """
        if df_raw is None or len(df_raw) < 50:
            return {"error": "Historique trop court pour le backtest (min 50 bougies)."}
            
        logger.info(f"⏳ [Backtest] Précalcul des indicateurs ({len(df_raw)} bougies)...")
        # 1. On calcule tous les indicateurs une seule fois pour la vitesse
        df_ind = self.indicator.compute_all(df_raw)
        df_ind = df_ind.dropna() # On retire les premières lignes (ex: les 200 premières pour l'EMA200)
        
        if df_ind.empty:
            return {"error": "Historique trop court après calcul de l'EMA 200."}

        # Variables d'état (Portefeuille local)
        capital = self.initial_capital
        position_size = 0.0 # Quantité de coins détenus
        entry_price = 0.0
        
        trades = []
        win_trades = 0
        loss_trades = 0

        logger.info(f"🚀 [Backtest] Début de la simulation (Capital départ: {capital}$) ...")
        
        # 2. Simulation passage d'ordre (boucle chronologique)
        # On commence à l'index 1 car la stratégie regarde la ligne précédente
        for i in range(1, len(df_ind)):
            # On recréé un dataframe miniature de 2 lignes pour ne pas tricher (look-ahead)
            current_slice = df_ind.iloc[i-1:i+1]
            
            signal_data = self.strategy.generate_signal(current_slice)
            signal = signal_data.get('signal', 'HOLD')
            current_price = signal_data.get('price', df_ind.iloc[i]['Close'])
            date = df_ind.index[i]
            
            if signal == "BUY" and position_size == 0:
                # Acheter
                investment = capital * risk_per_trade
                position_size = investment / current_price
                capital -= investment
                entry_price = current_price
                
                trades.append({
                    "date": date, "type": "BUY", "price": current_price, "amount": position_size
                })
                
            elif signal == "SELL" and position_size > 0:
                # Vente totale de la position
                gain = position_size * current_price
                capital += gain
                
                profit_pct = (current_price - entry_price) / entry_price * 100
                if profit_pct > 0: win_trades += 1
                else: loss_trades += 1
                
                trades.append({
                    "date": date, "type": "SELL", "price": current_price, 
                    "profit_pct": profit_pct, "capital_after": capital
                })
                
                position_size = 0.0
                entry_price = 0.0

        # Vente finale de clôture forcée si à la fin du backtest on a toujours une position ouverte
        if position_size > 0:
            final_price = df_ind.iloc[-1]['Close']
            capital += position_size * final_price
            profit_pct = (final_price - entry_price) / entry_price * 100
            if profit_pct > 0: win_trades += 1
            else: loss_trades += 1

        total_trades = win_trades + loss_trades
        net_profit = capital - self.initial_capital
        roi_pct = (net_profit / self.initial_capital) * 100
        win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0.0
        
        logger.info(f"🏁 [Backtest] Fin. Net Profit: {net_profit:.2f}$ ({roi_pct:.2f}%). Win Rate: {win_rate:.1f}%")

        return {
            "initial_capital": self.initial_capital,
            "final_capital": capital,
            "net_profit": net_profit,
            "roi_pct": roi_pct,
            "total_trades": total_trades,
            "win_rate": win_rate,
            "trades_log": trades
        }
