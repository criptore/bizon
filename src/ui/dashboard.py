import logging
import sys
import os

# Fix Jinja2 compatibility with Python 3.14

# Fix Jinja2 compatibility with Python 3.14
try:
    import jinja2
    from jinja2 import utils as _jutils
    from jinja2 import loaders as _jloaders

    # 1. Patch LRUCache lookup (TypeError on unhashable dict as key)
    _orig_lru_getitem = _jutils.LRUCache.__getitem__
    def _safe_lru_getitem(self, key):
        try: return _orig_lru_getitem(self, key)
        except TypeError: 
            # On continue sans cache si la clé est invalide (dict)
            return None
    _jutils.LRUCache.__getitem__ = _safe_lru_getitem

    # 2. Patch split_template_path (AttributeError when 'template' is a dict)
    def _safe_split_template_path(template):
        if isinstance(template, dict): return []
        if not hasattr(template, "split") and hasattr(template, "__str__"):
            template = str(template)
        # On définit en dur la fonction pour écraser toute version chargée
        pieces = []
        for piece in str(template).split("/"):
            if os.path.isabs(piece) or ".." in piece: continue
            pieces.append(piece)
        return pieces
    _jloaders.split_template_path = _safe_split_template_path

    # INTERVENTION FINALE : Patch Starlette (Fix breaking change TemplateResponse)
    import starlette.templating
    from starlette.requests import Request
    _orig_TemplateResponse = starlette.templating.Jinja2Templates.TemplateResponse
    
    def _safe_TemplateResponse(self, *args, **kwargs):
        # En Starlette >= 0.38, la signature est (request, name, context, ...)
        # Mais Gradio appelle (name, context, ...)
        if len(args) > 0 and isinstance(args[0], str):
            # C'est l'appel à l'ancienne (Gradio -> Starlette < 0.38)
            name = args[0]
            context = args[1] if len(args) > 1 else kwargs.get("context", {})
            request = context.get("request") if isinstance(context, dict) else None
            return _orig_TemplateResponse(self, request=request, name=name, context=context)
        return _orig_TemplateResponse(self, *args, **kwargs)
        
    starlette.templating.Jinja2Templates.TemplateResponse = _safe_TemplateResponse

    # 4. Patch Gradio (Frontend ValueError fix)
    import os
    import pathlib
    _orig_exists_os = os.path.exists
    _orig_exists_path = pathlib.Path.exists
    
    def _safe_exists_os(path):
        if "frontend" in str(path) and "index.html" in str(path): return True
        return _orig_exists_os(path)
        
    def _safe_exists_path(self):
        if "frontend" in str(self) and "index.html" in str(self): return True
        return _orig_exists_path(self)
        
    os.path.exists = _safe_exists_os
    pathlib.Path.exists = _safe_exists_path

    print("[SYSTEM] Correctifs de stabilité ALPHA (Python 3.14) injectés avec succès.")
except Exception as e:
    print(f"[SYSTEM] Échec de l'injection des correctifs ALPHA : {e}")

import matplotlib
matplotlib.use("Agg")  # Force backend non-interactif

# Configuration du logging pour le processus autonome
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

import gradio as gr
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import time

from src.datafeed import DataFetcher
from src.engine import IndicatorEngine
from src.config import config

logger = logging.getLogger("CassandreDashboard")

def _plot_candlestick(df: pd.DataFrame, ticker: str) -> go.Figure:
    """Créé la visualisation de l'actif avec tous ses indicateurs techniques."""
    # Création des sous-graphiques avec des hauteurs ajustées
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, 
        vertical_spacing=0.03, 
        row_heights=[0.6, 0.2, 0.2],
        subplot_titles=(f"{ticker} - Prix & Tendance", "Indicateur MACD", "Oscillateur RSI")
    )

    # 1. Graphique Principal : Candlestick + BB + EMA
    # Bypass total pour Python 3.14 Alpha : On convertit tout en listes simples
    dates_list = df.index.strftime('%Y-%m-%d').tolist()
    close_list = df['Close'].tolist()
    open_list = df['Open'].tolist()
    high_list = df['High'].tolist()
    low_list = df['Low'].tolist()

    # Ajout du prix (Ligne de secours invisible ou visible selon besoin)
    fig.add_trace(go.Scatter(
        x=dates_list, y=close_list, name="Prix (Ligne)",
        line=dict(color='#00FF00', width=1),
        opacity=0.5
    ), row=1, col=1)

    fig.add_trace(go.Candlestick(
        x=dates_list, open=open_list, high=high_list, low=low_list, close=close_list,
        name="Prix (Bougies)",
        increasing=dict(line=dict(color='#00FF00')),
        decreasing=dict(line=dict(color='#FF4500'))
    ), row=1, col=1)

    # EMA 50 et EMA 200
    if "EMA_50" in df.columns:
        fig.add_trace(go.Scatter(x=dates_list, y=df['EMA_50'].tolist(), line=dict(color='#FFA500', width=2), name="EMA 50"), row=1, col=1)
    if "EMA_200" in df.columns:
        fig.add_trace(go.Scatter(x=dates_list, y=df['EMA_200'].tolist(), line=dict(color='#00BFFF', width=2), name="EMA 200"), row=1, col=1)

    # Bande de Bollinger
    if "BB_Upper" in df.columns and "BB_Lower" in df.columns:
        fig.add_trace(go.Scatter(
            x=dates_list + dates_list[::-1],
            y=df['BB_Upper'].tolist() + df['BB_Lower'].tolist()[::-1],
            fill='toself', fillcolor='rgba(150, 150, 200, 0.1)', line=dict(color='rgba(255,255,255,0)'),
            name="Bandes de Bollinger", showlegend=False
        ), row=1, col=1)

    # 2. Graphique Secondaire : MACD
    if all(k in df.columns for k in ["MACD", "MACD_Signal", "MACD_Hist"]):
        hist_list = df['MACD_Hist'].tolist()
        colors = ['#00FF00' if val >= 0 else '#FF4500' for val in hist_list]
        fig.add_trace(go.Bar(x=dates_list, y=hist_list, marker_color=colors, name="MACD Hist"), row=2, col=1)
        fig.add_trace(go.Scatter(x=dates_list, y=df['MACD'].tolist(), line=dict(color='#00BFFF', width=1.5), name="MACD"), row=2, col=1)
        fig.add_trace(go.Scatter(x=dates_list, y=df['MACD_Signal'].tolist(), line=dict(color='#FFA500', width=1.5), name="Signal"), row=2, col=1)

    # 3. Graphique Tertiaire : RSI
    if "RSI" in df.columns:
        fig.add_trace(go.Scatter(x=dates_list, y=df['RSI'].tolist(), line=dict(color='#DDA0DD', width=2), name="RSI"), row=3, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color="rgba(255, 0, 0, 0.5)", row=3, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="rgba(0, 255, 0, 0.5)", row=3, col=1)
        fig.update_yaxes(range=[0, 100], row=3, col=1)

    # Cosmétique Globale
    fig.update_layout(
        template="plotly_dark", 
        margin=dict(l=30, r=20, t=40, b=20),
        xaxis_rangeslider_visible=False,
        height=750,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    # Force auto-range pour éviter l'écrasement à 0
    fig.update_yaxes(autorange=True, row=1, col=1)
    fig.update_yaxes(autorange=True, row=2, col=1)
    
    return fig

def update_ui(ticker: str, period: str, interval: str):
    logger.info(f"[UI_EVENT] Demande d'actualisation : {ticker} | {period} | {interval}")
    try:
        # Téléchargement DataFeed
        logger.info(f"[DATA] Récupération des données historiques pour {ticker}...")
        fetcher = DataFetcher(use_cache=True)
        # On force la maj pour réagir aux dropdowns instantanément
        df_raw = fetcher.fetch_historical_data(ticker, period=period, interval=interval, force_refresh=True)
        
        if df_raw is None or df_raw.empty:
            logger.error(f"[DATA] Échec de récupération pour {ticker}")
            return None, f"❌ Erreur : Impossible de récupérer l'historique pour {ticker}."
            
        # Calcul des indicateurs (Cassandre Native - pas de dropna pour garder l'affichage)
        logger.info(f"[ENGINE] Calcul des indicateurs techniques...")
        engine = IndicatorEngine()
        df_processed = engine.compute_all(df_raw)
        
        # On ne garde que la période demandée pour l'affichage final (on enlève le buffer de calcul)
        # Mais on garde assez pour voir l'EMA stable
        display_limit = 365
        if period == "3mo": display_limit = 95
        elif period == "6mo": display_limit = 185
        elif period == "2y": display_limit = 735
        
        df_final = df_processed.tail(display_limit)
        
        if df_final is None or df_final.empty:
            logger.warning(f"[ENGINE] Historique trop court pour EMA 200 sur {ticker}")
            return None, "❌ Erreur : Historique insuffisant pour calculer l'EMA 200."
            
        # DEBUG : Affichage du snapshot des données dans le terminal
        print("\n--- [DEBUG CASSANDRE] Snapshot des données envoyées au graphique ---")
        print(df_final[['Open', 'High', 'Low', 'Close', 'EMA_200']].tail(5))
        print(f"Nombre total de points affichés : {len(df_final)} (sur {len(df_processed)} calculés)")
        print("------------------------------------------------------------------\n")
            
        # DEBUG : Export CSV pour inspection interne
        try:
            df_final.to_csv("debug_cassandre_data.csv")
            print(f"📁 [DEBUG] Données exportées dans debug_cassandre_data.csv")
        except:
            pass
            
        fig = _plot_candlestick(df_final, ticker)
        logger.info(f"[UI] Graphique généré avec succès ({len(df_processed)} bougies).")
        return fig, f"✅ Graphique actualisé pour **{ticker}**."
        
    except Exception as e:
        logger.exception(f"[ERROR] Erreur imprévue dans update_ui")
        return None, f"❌ Erreur interne : {str(e)}"

def launch_dashboard(share=False, standalone=True):
    # Thème doux inspiré du cahier des charges UX (tons chauds)
    theme = gr.themes.Soft(
        primary_hue="amber",
        neutral_hue="stone",
        font=[gr.themes.GoogleFont("Outfit"), "Arial", "sans-serif"]
    )
    
    with gr.Blocks(theme=theme, title="Cassandre Dashboard") as demo:
        # ... (le reste de l'UI reste identique)
        gr.Markdown("<h1 style='text-align: center; color: #7A4E2D; margin-top:20px;'>🔮 Cassandre Terminal — Mode Visualisation</h1>")
        
        with gr.Row():
            with gr.Column(scale=1, variant="panel"):
                gr.Markdown("### ⚙️ Centre de Contrôle")
                
                ticker_drop = gr.Dropdown(
                    choices=["BTC-USD", "ETH-USD", "AAPL", "MSFT", "TSLA", "NVDA"], 
                    value="BTC-USD", label="Actif Financier", interactive=True
                )
                
                period_drop = gr.Dropdown(
                    choices=["3mo", "6mo", "1y", "2y", "5y"], 
                    value="1y", label="Profondeur Historique", interactive=True
                )
                
                interval_drop = gr.Dropdown(
                    choices=["1d", "1wk"], 
                    value="1d", label="Bougies (Intervalle)", interactive=True
                )
                
                update_btn = gr.Button("📊 Actualiser l'analyse", variant="primary")
                
                gr.Markdown(f"### 💻 Composants Système")
                gr.Markdown(f"<span style='color: #4A7A4A; font-weight: bold;'>{config.hardware_badge}</span>")
                gr.Markdown(f"<span style='color: #7A4E2D; font-size:0.9em;'>Batch : {config.batch_size} | Vitesse de calcul allouée : {config.calc_frequency_ms}ms</span>")
                
                status_md = gr.Markdown("🟢 Prêt.")

            with gr.Column(scale=4):
                plot_output = gr.Plot(label="Graphiques Financiers")

        update_btn.click(
            fn=update_ui,
            inputs=[ticker_drop, period_drop, interval_drop],
            outputs=[plot_output, status_md]
        )
        
        demo.load(
            fn=update_ui,
            inputs=[ticker_drop, period_drop, interval_drop],
            outputs=[plot_output, status_md]
        )

    import webbrowser
    import sys
    import time
    import urllib.request

    # Mode App natif (fenêtre webview) activé sur Mac ET Windows
    standalone_mode = standalone and sys.platform in ("win32", "darwin")

    if standalone_mode:
        # ----------------------------------------------------------------
        # Gradio 4.44.1 lève ValueError("localhost not accessible") même
        # quand le serveur démarre bien — bug de sa vérification interne.
        # On court-circuite ce check pour éviter l'erreur.
        # ----------------------------------------------------------------
        try:
            from gradio import networking as _gn
            _gn.url_ok = lambda url: True
            
            # Patch de sécurité global pour les Locks (TypeError NoneType sur 3.14)
            import gradio.queueing
            import asyncio
            def _robust_lock():
                try: return asyncio.Lock()
                except RuntimeError:
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        return asyncio.Lock()
                    except Exception: return None
            gradio.queueing.safe_get_lock = _robust_lock
            
        except Exception:
            pass

        # Tuer tout processus qui occupe le port 7860 (reste d'une session précédente)
        # Tuer tout processus qui occupe le port 7860 (reste d'une session précédente)
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'connections']):
                try:
                    for conn in (proc.connections() or []):
                        if hasattr(conn, 'laddr') and conn.laddr.port == 7860:
                            logger.info(f"Arrêt du processus résiduel sur port 7860 (pid={proc.pid})")
                            proc.kill()
                            break
                except Exception:
                    pass
        except Exception:
            pass

        # Démarrage Gradio non-bloquant avec Queue activée
        local_url = "http://127.0.0.1:7860"
        try:
            demo.queue() # <-- Indispensable pour éviter TypeError Lock NoneType
            result = demo.launch(
                share=False,
                inline=False,
                inbrowser=False,
                prevent_thread_lock=True,
                server_name="127.0.0.1",
                quiet=True
            )
            # result = (app, local_url, share_url)
            if result and len(result) >= 2 and result[1]:
                local_url = result[1].rstrip('/')
        except Exception as e:
            logger.warning(f"Gradio launch warning: {e}")
        logger.info(f"URL Gradio : {local_url}")

        # Attendre que le serveur réponde (max 10 secondes)
        # HTTPError (4xx/5xx) = serveur UP mais erreur de contenu → on continue quand même
        import urllib.error
        server_ready = False
        for _ in range(50):
            try:
                urllib.request.urlopen(local_url, timeout=1)
                server_ready = True
                break
            except urllib.error.HTTPError:
                # Le serveur répond (même avec une erreur) → il est démarré
                server_ready = True
                break
            except Exception:
                time.sleep(0.2)

        if not server_ready:
            logger.error("Serveur Gradio vraiment inaccessible après 10s.")
            webbrowser.open(local_url)
            while True:
                time.sleep(10)

        # Tenter d'ouvrir une fenêtre native, sinon navigateur
        try:
            import webview
            platform_name = "Windows" if sys.platform == "win32" else "Mac"
            logger.info(f"Ouverture App Cassandre ({platform_name}) → {local_url}")
            window = webview.create_window("Cassandre Terminal", local_url, width=1200, height=800)
            webview.start()  # Bloque jusqu'à fermeture de la fenêtre
        except Exception as e:
            logger.warning(f"Webview indisponible ({e}). Ouverture navigateur…")
            webbrowser.open(local_url)
            while True:
                time.sleep(10)
    else:
        # Mode navigateur standard (non-standalone)
        demo.launch(share=share, inline=False, inbrowser=True, prevent_thread_lock=False)


