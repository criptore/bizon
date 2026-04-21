import logging
import sys
import os
import time
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import gradio as gr

# Patches de stabilité pour Python 3.14
try:
    import jinja2
    from jinja2 import utils as _jutils
    from jinja2 import loaders as _jloaders
    _orig_lru_getitem = _jutils.LRUCache.__getitem__
    def _safe_lru_getitem(self, key):
        try: return _orig_lru_getitem(self, key)
        except TypeError: return None
    _jutils.LRUCache.__getitem__ = _safe_lru_getitem
    import starlette.templating
    _orig_TemplateResponse = starlette.templating.Jinja2Templates.TemplateResponse
    def _safe_TemplateResponse(self, *args, **kwargs):
        if len(args) > 0 and isinstance(args[0], str):
            name = args[0]
            context = args[1] if len(args) > 1 else kwargs.get("context", {})
            request = context.get("request") if isinstance(context, dict) else None
            return _orig_TemplateResponse(self, request=request, name=name, context=context)
        return _orig_TemplateResponse(self, *args, **kwargs)
    starlette.templating.Jinja2Templates.TemplateResponse = _safe_TemplateResponse
except Exception: pass

import matplotlib
matplotlib.use("Agg")

from src.datafeed import DataFetcher
from src.engine import IndicatorEngine
from src.config import config
from src.broker.binance_broker import BinanceBroker
from src.engine.backtester import Backtester
from src.engine.pipeline import TradingPipeline

logger = logging.getLogger("CassandreDashboard")

# Instances Globales
broker_instance = BinanceBroker()
broker_connected = broker_instance.connect()
pipeline_instance = TradingPipeline(use_broker=True)

def _plot_candlestick(df: pd.DataFrame, ticker: str) -> go.Figure:
    """Tracé ultra-diagnostique avec fallback de sécurité."""
    if df is None or df.empty:
        logger.warning(f"⚠️ [_plot_candlestick] DataFrame VIDE pour {ticker}")
        return go.Figure()

    # LOGS DE DIAGNOSTIC PROFOND
    logger.info(f"🔍 [DEBUG] Diagnostic Graphique pour {ticker}")
    logger.info(f"🔍 [DEBUG] Nombre de lignes: {len(df)}")
    logger.info(f"🔍 [DEBUG] Colonnes disponibles: {df.columns.tolist()}")
    logger.info(f"🔍 [DEBUG] Types de données: {df.dtypes.to_dict()}")
    logger.info(f"🔍 [DEBUG] Index: {type(df.index)} (Taille: {len(df.index)})")
    
    if len(df) > 0:
        logger.info(f"🔍 [DEBUG] Valeurs de la dernière ligne:\n{df.iloc[-1].to_dict()}")

    # On s'assure d'avoir assez de points
    if len(df) < 5:
        logger.warning(f"⚠️ [_plot_candlestick] Données insuffisantes (<5 lignes) pour {ticker}")
        return go.Figure()

    # On prend les 300 derniers points pour la vue temps réel
    df_plot = df.tail(300)
    
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, 
        vertical_spacing=0.03, 
        row_heights=[0.6, 0.2, 0.2],
        subplot_titles=("Prix & EMAs", "MACD", "RSI")
    )

    # 1. Tentative de tracé Chandeliers
    try:
        fig.add_trace(go.Candlestick(
            x=df_plot.index,
            open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'],
            name="Bougies", 
            increasing_line_color='#26a69a', 
            decreasing_line_color='#ef5350'
        ), row=1, col=1)
        logger.info("✅ [DEBUG] Trace Candlestick ajoutée avec succès.")
    except Exception as e:
        logger.error(f"❌ [DEBUG] Échec Candlestick : {e}. Utilisation du FALLBACK (Ligne).")
        # FALLBACK : Tracé ligne simple si les bougies échouent
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['Close'], name="Prix (Ligne)", line=dict(color='#00FF00', width=2)), row=1, col=1)

    # 2. EMAs
    if "EMA_50" in df_plot.columns:
        ema50 = df_plot['EMA_50'].dropna()
        fig.add_trace(go.Scatter(x=ema50.index, y=ema50, name="EMA 50", line=dict(color='#FFA500', width=1)), row=1, col=1)
    
    if "EMA_200" in df_plot.columns:
        ema200 = df_plot['EMA_200'].dropna()
        fig.add_trace(go.Scatter(x=ema200.index, y=ema200, name="EMA 200", line=dict(color='#00BFFF', width=1)), row=1, col=1)

    # 3. RSI
    if "RSI" in df_plot.columns:
        rsi = df_plot['RSI'].dropna()
        fig.add_trace(go.Scatter(x=rsi.index, y=rsi, name="RSI", line=dict(color='#DDA0DD', width=1.5)), row=3, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color="red", row=3, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="green", row=3, col=1)
        fig.update_yaxes(range=[0, 100], row=3, col=1)

    # 4. MACD
    if "MACD_Hist" in df_plot.columns:
        fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['MACD_Hist'], name="MACD Hist", marker_color='#78909c'), row=2, col=1)

    fig.update_layout(
        template="plotly_dark", 
        xaxis_rangeslider_visible=False, 
        height=750, 
        margin=dict(l=10, r=10, t=40, b=10)
    )
    return fig

def update_ui(ticker: str, profile_name: str):
    logger.info(f"🔄 [DASHBOARD] Début Update UI pour {ticker} ({profile_name})")
    try:
        fetcher = DataFetcher(use_cache=False)
        # On force la récupération Binance pour le direct
        df_raw = fetcher.fetch_historical_data(ticker, period="3d", interval="1m", force_refresh=True)
        if df_raw is None or df_raw.empty:
            logger.error(f"❌ [DASHBOARD] Échec Fetcher pour {ticker}")
            return None, "❌ Erreur de récupération Binance.", "🔴 Hors-ligne"
            
        logger.info(f"✅ [DASHBOARD] Données brutes reçues : {len(df_raw)} lignes.")
        engine = IndicatorEngine()
        df_processed = engine.compute_all(df_raw)
        logger.info(f"✅ [DASHBOARD] Calcul indicateurs terminé : {len(df_processed)} lignes.")
        
        fig = _plot_candlestick(df_processed, ticker)
        
        balance = broker_instance.get_balance("USDT") if broker_connected else 0.0
        testnet = " (Testnet)" if broker_instance.is_testnet else ""
        broker_text = f"🟢 **{profile_name}**{testnet} | 💰 **{balance:.2f} USDT**" if broker_connected else f"🔴 Déconnecté ({profile_name})"
        
        return fig, f"⚡ MAJ Auto: {time.strftime('%H:%M:%S')}", broker_text
    except Exception as e:
        logger.error(f"❌ [DASHBOARD] Erreur FATALE update_ui: {e}", exc_info=True)
        return None, f"❌ Erreur Système : {e}", "🔴 ERREUR"

def run_backtest_ui(ticker: str, period: str, profile_name: str):
    try:
        fetcher = DataFetcher(use_cache=True)
        df_raw = fetcher.fetch_historical_data(ticker, period=period, interval="15m")
        if df_raw is None: return "❌ Erreur données."
        tester = Backtester(use_ai=True, profile_name=profile_name)
        res = tester.run(df_raw)
        if "error" in res: return f"⚠️ {res['error']}"
        return (
            f"### 📊 RÉSULTATS {profile_name}\n"
            f"| Métrique | Valeur |\n"
            f"| :--- | :--- |\n"
            f"| 💰 **CAPITAL FINAL** | **{res['final_capital']:.2f} $** |\n"
            f"| 📈 **ROI TOTAL** | {res['roi_pct']:.2f} % |\n"
            f"| ⚖️ **RATIO SHARPE** | {res['sharpe_ratio']:.2f} |\n"
            f"| 📉 **MAX DRAWDOWN** | -{res['max_drawdown_pct']:.2f} % |\n"
            f"| 🎯 **WIN RATE** | {res['win_rate']:.1f} % ({res['total_trades']} trades) |\n"
        )
    except Exception as e: return f"❌ {e}"

def start_bot_ui(ticker: str, profile_name: str):
    pipeline_instance.set_profile(profile_name)
    for log in pipeline_instance.live_trading_loop(symbol=ticker):
        yield log

def stop_bot_ui():
    pipeline_instance.stop_bot()
    return "🛑 Arrêt du robot."

def launch_dashboard(share=False, standalone=True):
    theme = gr.themes.Soft(primary_hue="amber", neutral_hue="stone", font=[gr.themes.GoogleFont("Outfit"), "Arial"])
    profiles = list(config.TRADING_PROFILES.keys())
    
    with gr.Blocks(theme=theme, title="Cassandre Terminal") as demo:
        gr.Markdown("<h1 style='text-align: center; color: #7A4E2D;'>🔮 Cassandre Intelligence</h1>")
        
        with gr.Tabs():
            with gr.TabItem("📊 Marchés (Auto-15s)"):
                with gr.Row():
                    with gr.Column(scale=1):
                        profile_drop = gr.Radio(choices=profiles, label="🔥 Profil", value="NORMAL ⚖️")
                        ticker_drop = gr.Dropdown(choices=["BTC-USD", "ETH-USD", "SOL-USD"], value="BTC-USD", label="Actif")
                        update_btn = gr.Button("🔄 Force Update", variant="secondary")
                        status_msg = gr.Markdown("⏳ Connexion...")
                        broker_status = gr.Markdown("...")
                    with gr.Column(scale=4):
                        plot_output = gr.Plot()

            with gr.TabItem("🤖 IA Lab & Backtest"):
                with gr.Row():
                    with gr.Column(scale=1):
                        profile_bot = gr.Radio(choices=profiles, label="🔥 Profil Expert", value="NORMAL ⚖️")
                        bt_ticker = gr.Dropdown(choices=["BTC-USD", "ETH-USD"], value="BTC-USD", label="Actif")
                        bt_period = gr.Dropdown(choices=["1y", "2y"], value="1y", label="Simuler")
                        bt_btn = gr.Button("▶️ Simuler", variant="primary")
                        gr.Markdown("---")
                        bot_start_btn = gr.Button("⚡ ALLUMER LE BOT", variant="primary")
                        bot_stop_btn = gr.Button("🛑 ARRÊTER", variant="stop")
                    with gr.Column(scale=2):
                        with gr.Tabs():
                            with gr.TabItem("📈 Synthèse"):
                                bt_results = gr.Markdown("> *Lancer pour voir les métriques.*")
                            with gr.TabItem("📟 Console"):
                                bot_logs = gr.Textbox(lines=15, interactive=False, value="IA Console Ready.")

        # LOGIQUE AUTO 15s
        timer = gr.Timer(15)
        timer.tick(fn=update_ui, inputs=[ticker_drop, profile_drop], outputs=[plot_output, status_msg, broker_status])
        demo.load(fn=update_ui, inputs=[ticker_drop, profile_drop], outputs=[plot_output, status_msg, broker_status])
        
        update_btn.click(fn=update_ui, inputs=[ticker_drop, profile_drop], outputs=[plot_output, status_msg, broker_status])
        bt_btn.click(fn=run_backtest_ui, inputs=[bt_ticker, bt_period, profile_bot], outputs=[bt_results])
        bot_start_btn.click(fn=start_bot_ui, inputs=[bt_ticker, profile_bot], outputs=[bot_logs])
        bot_stop_btn.click(fn=stop_bot_ui, inputs=[], outputs=[bot_logs])

    if standalone and sys.platform in ("win32", "darwin"):
        import gradio.queueing, asyncio, webview, webbrowser
        def _l(): 
            try: return asyncio.Lock()
            except: return None
        gradio.queueing.safe_get_lock = _l
        demo.queue()
        demo.launch(share=False, prevent_thread_lock=True, quiet=True)
        time.sleep(3)
        try:
            webview.create_window("Cassandre Terminal", "http://127.0.0.1:7860", width=1280, height=850)
            webview.start()
        except: webbrowser.open("http://127.0.0.1:7860")
    else:
        demo.launch(share=share)

if __name__ == "__main__": launch_dashboard()
