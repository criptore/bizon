import gradio as gr
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import logging

from src.datafeed import DataFetcher
from src.engine import IndicatorEngine
from src.config import config

logger = logging.getLogger("BizonDashboard")

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
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name="Prix", increasing_line_color='green', decreasing_line_color='red'
    ), row=1, col=1)

    # EMA 50 et EMA 200
    if "EMA_50" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_50'], line=dict(color='#FFA500', width=1.5), name="EMA 50"), row=1, col=1)
    if "EMA_200" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_200'], line=dict(color='#00BFFF', width=1.5), name="EMA 200"), row=1, col=1)

    # Bande de Bollinger
    if "BB_Upper" in df.columns and "BB_Lower" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index.tolist() + df.index[::-1].tolist(),
            y=df['BB_Upper'].tolist() + df['BB_Lower'][::-1].tolist(),
            fill='toself', fillcolor='rgba(150, 150, 200, 0.1)', line=dict(color='rgba(255,255,255,0)'),
            name="Bande de Bollinger", showlegend=False
        ), row=1, col=1)

    # 2. Graphique Secondaire : MACD
    if all(k in df.columns for k in ["MACD", "MACD_Signal", "MACD_Hist"]):
        # Histogramme en vert et rouge
        colors = ['rgba(0, 255, 0, 0.6)' if val >= 0 else 'rgba(255, 0, 0, 0.6)' for val in df['MACD_Hist']]
        fig.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], marker_color=colors, name="MACD Hist"), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], line=dict(color='#00BFFF', width=1.5), name="MACD"), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD_Signal'], line=dict(color='#FFA500', width=1.5), name="Signal"), row=2, col=1)

    # 3. Graphique Tertiaire : RSI
    if "RSI" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#DDA0DD', width=1.5), name="RSI"), row=3, col=1)
        # Lignes horizontales 30 et 70
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
    
    return fig

def update_ui(ticker: str, period: str, interval: str):
    try:
        # Téléchargement DataFeed
        fetcher = DataFetcher(use_cache=True)
        # On force la maj pour réagir aux dropdowns instantanément
        df_raw = fetcher.fetch_historical_data(ticker, period=period, interval=interval, force_refresh=True)
        
        if df_raw is None or df_raw.empty:
            return None, f"❌ Erreur : Impossible de récupérer l'historique pour {ticker}."
            
        # Calcul des indicateurs de façon vectorielle
        engine = IndicatorEngine()
        df_processed = engine.compute_all(df_raw, dropna=True)
        
        if df_processed is None or df_processed.empty:
            return None, "❌ Erreur : Historique insuffisant pour calculer l'EMA 200 (essayez d'augmenter la période)."
            
        fig = _plot_candlestick(df_processed, ticker)
        return fig, f"✅ Graphique actualisé pour **{ticker}** ({len(df_processed)} périodes affichées)."
        
    except Exception as e:
        return None, f"❌ Erreur interne : {str(e)}"

def launch_dashboard(share=False, standalone=True):
    # Thème doux inspiré du cahier des charges UX (tons chauds)
    theme = gr.themes.Soft(
        primary_hue="amber",
        neutral_hue="stone",
        font=[gr.themes.GoogleFont("Outfit"), "Arial", "sans-serif"]
    )
    
    with gr.Blocks(theme=theme, title="Bizon Dashboard") as demo:
        # ... (le reste de l'UI reste identique)
        gr.Markdown("<h1 style='text-align: center; color: #7A4E2D; margin-top:20px;'>🦬 Bizon Terminal — Mode Visualisation</h1>")
        
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

    # Mode App natif (fenêtre webview) activé sur Mac ET Windows
    standalone_mode = standalone and sys.platform in ("win32", "darwin")

    if standalone_mode:
        # Gradio en arrière-plan (non-bloquant) pour que webview prenne le thread principal
        # server_name="127.0.0.1" force IPv4 et évite l'erreur "localhost not accessible" sur macOS
        try:
            _, local_url, _ = demo.launch(
                share=False,
                inline=False,
                inbrowser=False,
                prevent_thread_lock=True,
                server_name="127.0.0.1",
                quiet=True
            )
        except Exception as e:
            logger.warning(f"Gradio launch error ({e}), falling back to default port...")
            local_url = "http://127.0.0.1:7860"
            demo.launch(share=False, inline=False, inbrowser=False,
                        prevent_thread_lock=True, quiet=True)

        # Attendre que le serveur Gradio soit prêt
        import urllib.request
        for _ in range(30):
            try:
                urllib.request.urlopen(local_url, timeout=1)
                break
            except Exception:
                time.sleep(0.2)

        try:
            import webview
            platform_name = "Windows" if sys.platform == "win32" else "Mac"
            logger.info(f"Démarrage de l'App Bizon ({platform_name}) sur {local_url}")
            window = webview.create_window('Bizon Terminal', local_url, width=1200, height=800)
            webview.start()  # Bloque jusqu'à fermeture de la fenêtre
        except Exception as e:
            logger.warning(f"Échec du mode App natif ({e}). Ouverture navigateur...")
            webbrowser.open(local_url)
            while True: time.sleep(10)
    else:
        # Mode navigateur standard (non-standalone)
        demo.launch(share=share, inline=False, inbrowser=True, prevent_thread_lock=False)


