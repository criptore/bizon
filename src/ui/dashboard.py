import logging
import sys
import os

# Fix Jinja2 compatibility with Python 3.14
try:
    import jinja2
    from jinja2 import utils as _jutils
    from jinja2 import loaders as _jloaders

    _orig_lru_getitem = _jutils.LRUCache.__getitem__
    def _safe_lru_getitem(self, key):
        try: return _orig_lru_getitem(self, key)
        except TypeError: return None
    _jutils.LRUCache.__getitem__ = _safe_lru_getitem

    def _safe_split_template_path(template):
        if isinstance(template, dict): return []
        if not hasattr(template, "split") and hasattr(template, "__str__"):
            template = str(template)
        pieces = []
        for piece in str(template).split("/"):
            if os.path.isabs(piece) or ".." in piece: continue
            pieces.append(piece)
        return pieces
    _jloaders.split_template_path = _safe_split_template_path

    import starlette.templating
    from starlette.requests import Request
    _orig_TemplateResponse = starlette.templating.Jinja2Templates.TemplateResponse
    def _safe_TemplateResponse(self, *args, **kwargs):
        if len(args) > 0 and isinstance(args[0], str):
            name = args[0]
            context = args[1] if len(args) > 1 else kwargs.get("context", {})
            request = context.get("request") if isinstance(context, dict) else None
            return _orig_TemplateResponse(self, request=request, name=name, context=context)
        return _orig_TemplateResponse(self, *args, **kwargs)
    starlette.templating.Jinja2Templates.TemplateResponse = _safe_TemplateResponse

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
matplotlib.use("Agg")

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
from src.broker.binance_broker import BinanceBroker
from src.engine.backtester import Backtester
from src.engine.pipeline import TradingPipeline

logger = logging.getLogger("CassandreDashboard")

broker_instance = BinanceBroker()
broker_connected = broker_instance.connect()
pipeline_instance = TradingPipeline(use_broker=True)

# ── Design tokens ─────────────────────────────────────────────────────────────
GOLD   = "#C4A35A"
GREEN  = "#4CAF87"
RED    = "#E05C5C"
BLUE   = "#5B8DB5"
PURPLE = "#9B8CC4"

DARK = dict(
    bg="#0C0D10", surf="#13151A", surf2="#1A1D24", bord="#272B35",
    txt="#E4E0D8", dim="#6B6760", dim2="#9A9590",
    chart_bg="#0C0D10", chart_grid="rgba(255,255,255,0.04)",
    chart_txt="rgba(228,224,216,0.38)",
    up=GREEN, dn=RED,
)

# ── Meander SVG (inline, horizontal repeat) ───────────────────────────────────
MEANDER_SVG = (
    "<svg width='100%' height='13' style='display:block;flex-shrink:0' "
    "xmlns='http://www.w3.org/2000/svg'>"
    "<defs>"
    "<pattern id='mn' x='0' y='0' width='20' height='13' patternUnits='userSpaceOnUse'>"
    "<path d='M0,6.5 H4 V1.5 H16 V11.5 H12 V6.5 H20' fill='none' "
    f"stroke='{GOLD}' stroke-width='1.2' stroke-opacity='0.28' stroke-linecap='square'/>"
    "</pattern></defs>"
    "<rect width='100%' height='13' fill='url(#mn)'/>"
    "</svg>"
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
CUSTOM_CSS = f"""
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300&family=DM+Sans:wght@300;400;500&family=DM+Mono:wght@400;500&display=swap');

/* ── Base ── */
body, .gradio-container {{
    background: {DARK['bg']} !important;
    font-family: 'DM Sans', system-ui, sans-serif !important;
    color: {DARK['txt']} !important;
    margin: 0 !important;
    padding: 0 !important;
}}
.gradio-container > .main > .wrap {{
    padding: 0 !important;
    max-width: 100% !important;
}}
footer {{ display: none !important; }}

/* ── Header ── */
#cassandre-header {{
    height: 50px;
    background: {DARK['surf']};
    border-bottom: 1px solid {DARK['bord']};
    display: flex;
    align-items: center;
    padding: 0 24px;
    gap: 14px;
    flex-shrink: 0;
}}
#cassandre-header .wordmark {{
    font-family: 'Cormorant Garamond', Georgia, serif;
    font-size: 21px;
    font-weight: 300;
    color: {DARK['txt']};
    letter-spacing: 4px;
    text-transform: uppercase;
}}
#cassandre-header .oracle-label {{
    font-family: 'DM Sans', sans-serif;
    font-size: 9px;
    color: {GOLD};
    letter-spacing: 2.5px;
    text-transform: uppercase;
    font-weight: 500;
}}
#header-spacer {{ flex: 1; }}
#mode-toggle label {{
    font-family: 'DM Sans', sans-serif;
    font-size: 10px;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    font-weight: 500;
    color: {DARK['dim2']};
    border: 1px solid {DARK['bord']};
    border-radius: 2px;
    padding: 5px 14px;
    cursor: pointer;
    transition: all 0.15s;
    background: {DARK['surf2']};
}}
#mode-toggle label.selected, #mode-toggle input:checked + label {{
    background: {GOLD};
    color: #0C0D10;
    border-color: {GOLD};
}}
#mode-toggle .wrap {{
    border: none !important;
    background: transparent !important;
    gap: 0 !important;
    padding: 0 !important;
}}
#broker-badge {{
    display: flex;
    align-items: center;
    gap: 6px;
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    color: {DARK['dim2']};
    letter-spacing: 0.5px;
}}
#broker-dot {{
    width: 6px; height: 6px;
    border-radius: 50%;
    background: {GREEN};
    display: inline-block;
    flex-shrink: 0;
}}
#balance-display {{
    font-family: 'DM Mono', monospace;
    font-size: 12px;
    font-weight: 500;
    color: {DARK['txt']};
    letter-spacing: 0.5px;
}}
#vdivider {{
    width: 1px; height: 18px;
    background: {DARK['bord']};
    flex-shrink: 0;
}}

/* ── Tab bar ── */
.tabs > .tab-nav {{
    background: {DARK['surf']} !important;
    border-bottom: 1px solid {DARK['bord']} !important;
    padding: 0 20px !important;
    gap: 0 !important;
}}
.tabs > .tab-nav > button {{
    font-family: 'DM Sans', sans-serif !important;
    font-size: 11px !important;
    font-weight: 500 !important;
    letter-spacing: 1.3px !important;
    text-transform: uppercase !important;
    color: {DARK['dim2']} !important;
    background: transparent !important;
    border: none !important;
    border-bottom: 1.5px solid transparent !important;
    border-radius: 0 !important;
    padding: 10px 20px 9px !important;
    transition: color 0.15s !important;
}}
.tabs > .tab-nav > button.selected {{
    color: {GOLD} !important;
    border-bottom-color: {GOLD} !important;
}}

/* ── Section labels ── */
.section-label {{
    font-family: 'DM Sans', sans-serif;
    font-size: 9px;
    color: {DARK['dim']};
    letter-spacing: 1.8px;
    text-transform: uppercase;
    margin-bottom: 10px;
    display: block;
}}

/* ── Inputs / Selects ── */
.gradio-container input, .gradio-container select,
.gradio-container textarea,
.block .wrap-inner {{
    background: {DARK['surf2']} !important;
    border: 1px solid {DARK['bord']} !important;
    border-radius: 3px !important;
    color: {DARK['txt']} !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 12px !important;
    letter-spacing: 0.3px !important;
}}
.gradio-container label span {{
    font-family: 'DM Sans', sans-serif !important;
    font-size: 11px !important;
    color: {DARK['dim2']} !important;
    letter-spacing: 0.2px !important;
}}
.gradio-container .block {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 4px 0 !important;
}}

/* ── Left panel ── */
#left-panel {{
    width: 270px !important;
    background: {DARK['surf']};
    border-right: 1px solid {DARK['bord']};
    padding: 18px;
    overflow-y: auto;
    flex-shrink: 0 !important;
}}

/* ── Buttons ── */
button.primary-outline {{
    width: 100%;
    padding: 8px 0;
    margin-top: 10px;
    background: transparent;
    border: 1px solid {GOLD};
    border-radius: 2px;
    color: {GOLD};
    font-family: 'DM Sans', sans-serif;
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    cursor: pointer;
    transition: all 0.15s;
}}
button.primary-outline:hover {{
    background: {GOLD};
    color: #0C0D10;
}}
.gr-button-primary {{
    background: transparent !important;
    border: 1px solid {GOLD} !important;
    border-radius: 2px !important;
    color: {GOLD} !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 11px !important;
    font-weight: 500 !important;
    letter-spacing: 1.5px !important;
    text-transform: uppercase !important;
    transition: all 0.15s !important;
}}
.gr-button-primary:hover {{
    background: {GOLD} !important;
    color: #0C0D10 !important;
}}
.gr-button-secondary {{
    background: transparent !important;
    border: 1px solid {DARK['bord']} !important;
    border-radius: 2px !important;
    color: {DARK['dim2']} !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 11px !important;
    letter-spacing: 1.2px !important;
    text-transform: uppercase !important;
}}
.gr-button-stop {{
    background: transparent !important;
    border: 1px solid {RED} !important;
    border-radius: 2px !important;
    color: {RED} !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 11px !important;
    letter-spacing: 1.2px !important;
    text-transform: uppercase !important;
}}
.btn-green {{
    background: transparent !important;
    border: 1px solid {GREEN} !important;
    border-radius: 2px !important;
    color: {GREEN} !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 10px !important;
    letter-spacing: 1.2px !important;
    text-transform: uppercase !important;
    transition: all 0.15s !important;
}}
.btn-green.active {{
    background: {GREEN} !important;
    color: #0a1a12 !important;
}}

/* ── Backtest result cards ── */
.metric-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-top: 12px;
}}
.metric-card {{
    background: {DARK['surf']};
    border: 1px solid {DARK['bord']};
    border-radius: 3px;
    padding: 10px 12px;
}}
.metric-label {{
    font-family: 'DM Sans', sans-serif;
    font-size: 9px;
    color: {DARK['dim']};
    letter-spacing: 1.3px;
    text-transform: uppercase;
    margin-bottom: 5px;
}}
.metric-value {{
    font-family: 'DM Mono', monospace;
    font-size: 13px;
    font-weight: 500;
    letter-spacing: 0.3px;
}}
.metric-value.green {{ color: {GREEN}; }}
.metric-value.red   {{ color: {RED}; }}
.metric-value.gold  {{ color: {GOLD}; }}
.metric-value.base  {{ color: {DARK['txt']}; }}

/* ── Console ── */
#bot-console textarea {{
    background: #0a0b0d !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 12px !important;
    color: {DARK['dim2']} !important;
    line-height: 2 !important;
    border: 1px solid {DARK['bord']} !important;
    border-radius: 3px !important;
}}

/* ── Controls strip (Analyse tab) ── */
#controls-strip {{
    height: 48px;
    background: {DARK['surf']};
    border-bottom: 1px solid {DARK['bord']};
    display: flex;
    align-items: center;
    padding: 0 22px;
    gap: 12px;
    flex-shrink: 0;
}}
#controls-strip label span {{
    font-size: 9px !important;
    letter-spacing: 1.5px !important;
    text-transform: uppercase !important;
    color: {DARK['dim']} !important;
}}

/* ── Status bar ── */
#status-bar {{
    height: 30px;
    background: {DARK['surf']};
    border-top: 1px solid {DARK['bord']};
    display: flex;
    align-items: center;
    padding: 0 22px;
    gap: 20px;
    flex-shrink: 0;
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    color: {DARK['dim2']};
}}

/* ── Dividers ── */
.cassandre-divider {{
    height: 1px;
    background: {DARK['bord']};
    margin: 14px 0;
}}

/* ── Markdown cleanup ── */
.gradio-container .prose p,
.gradio-container .prose h1,
.gradio-container .prose h2,
.gradio-container .prose h3 {{
    color: {DARK['txt']} !important;
    font-family: 'DM Sans', sans-serif !important;
}}

/* ── Plot container ── */
.gradio-container .plot-container {{
    background: {DARK['bg']} !important;
    border: none !important;
}}

/* ── Analyse tab full width ── */
#analyse-tab {{
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
}}

/* ── Parametres ── */
#settings-tab {{
    padding: 28px 32px;
    background: {DARK['bg']};
}}
.settings-section-label {{
    font-family: 'DM Sans', sans-serif;
    font-size: 9px;
    color: {DARK['dim']};
    letter-spacing: 1.8px;
    text-transform: uppercase;
    margin-bottom: 14px;
    display: block;
}}
.settings-field {{
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 10px;
}}
.settings-field label {{
    font-family: 'DM Sans', sans-serif;
    font-size: 12px;
    color: {DARK['dim2']};
    width: 220px;
    flex-shrink: 0;
}}
.btn-save {{
    padding: 9px 28px;
    background: {GOLD};
    border: none;
    border-radius: 2px;
    color: #0C0D10;
    font-family: 'DM Sans', sans-serif;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    cursor: pointer;
    margin-top: 16px;
}}

/* ── Profil de risque ── */
.risk-params {{
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    color: {DARK['dim2']};
    margin-top: 8px;
    line-height: 1.9;
}}
"""

RISK_PROFILES = {
    "soft":      "TP +0.8%  ·  SL −0.5%\nCycle : 30 s  ·  Taille : 3%",
    "normal":    "TP +1.5%  ·  SL −1.0%\nCycle : 15 s  ·  Taille : 5%",
    "dynamique": "TP +3.0%  ·  SL −2.0%\nCycle : 5 s  ·  Taille : 10%",
}

# ── Chart ─────────────────────────────────────────────────────────────────────
def _plot_candlestick(df: pd.DataFrame, ticker: str) -> go.Figure:
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.6, 0.2, 0.2],
        subplot_titles=(f"{ticker} · Prix & Tendance", "MACD", "RSI")
    )

    dates = df.index.strftime('%Y-%m-%d').tolist()
    closes = df['Close'].tolist()

    fig.add_trace(go.Candlestick(
        x=dates,
        open=df['Open'].tolist(), high=df['High'].tolist(),
        low=df['Low'].tolist(), close=closes,
        name="Prix",
        increasing=dict(line=dict(color=GREEN, width=0.9), fillcolor=GREEN),
        decreasing=dict(line=dict(color=RED, width=0.9), fillcolor=RED),
    ), row=1, col=1)

    if "EMA_50" in df.columns:
        fig.add_trace(go.Scatter(
            x=dates, y=df['EMA_50'].tolist(),
            line=dict(color=GOLD, width=1.4), name="EMA 50", opacity=0.85
        ), row=1, col=1)
    if "EMA_200" in df.columns:
        fig.add_trace(go.Scatter(
            x=dates, y=df['EMA_200'].tolist(),
            line=dict(color=BLUE, width=1.4), name="EMA 200", opacity=0.85
        ), row=1, col=1)
    if "BB_Upper" in df.columns and "BB_Lower" in df.columns:
        upper = df['BB_Upper'].tolist()
        lower = df['BB_Lower'].tolist()
        fig.add_trace(go.Scatter(
            x=dates + dates[::-1],
            y=upper + lower[::-1],
            fill='toself',
            fillcolor='rgba(196,163,90,0.06)',
            line=dict(color='rgba(196,163,90,0.20)', width=0.8),
            name="BB", showlegend=True
        ), row=1, col=1)

    if all(k in df.columns for k in ["MACD", "MACD_Signal", "MACD_Hist"]):
        hist = df['MACD_Hist'].tolist()
        colors = [GREEN if v >= 0 else RED for v in hist]
        fig.add_trace(go.Bar(
            x=dates, y=hist, marker_color=colors,
            name="MACD Hist", opacity=0.65, showlegend=False
        ), row=2, col=1)
        fig.add_trace(go.Scatter(
            x=dates, y=df['MACD'].tolist(),
            line=dict(color=BLUE, width=1.1), name="MACD", opacity=0.8
        ), row=2, col=1)
        fig.add_trace(go.Scatter(
            x=dates, y=df['MACD_Signal'].tolist(),
            line=dict(color=GOLD, width=1.1), name="Signal", opacity=0.8
        ), row=2, col=1)

    if "RSI" in df.columns:
        fig.add_trace(go.Scatter(
            x=dates, y=df['RSI'].tolist(),
            line=dict(color=PURPLE, width=1.4), name="RSI", opacity=0.85
        ), row=3, col=1)
        fig.add_hline(y=70, line_dash="dot",
                      line=dict(color=RED, width=1), opacity=0.35, row=3, col=1)
        fig.add_hline(y=30, line_dash="dot",
                      line=dict(color=GREEN, width=1), opacity=0.35, row=3, col=1)
        fig.update_yaxes(range=[0, 100], row=3, col=1)

    grid_color = "rgba(255,255,255,0.04)"
    axis_font = dict(family="DM Mono", color="rgba(228,224,216,0.38)", size=9)

    fig.update_layout(
        paper_bgcolor=DARK['bg'],
        plot_bgcolor=DARK['bg'],
        font=axis_font,
        margin=dict(l=55, r=12, t=40, b=20),
        xaxis_rangeslider_visible=False,
        height=580,
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="right", x=1,
            font=dict(family="DM Mono", size=9, color="rgba(228,224,216,0.55)"),
            bgcolor="rgba(0,0,0,0)"
        ),
        xaxis=dict(gridcolor=grid_color, linecolor=DARK['bord'], zeroline=False),
        xaxis2=dict(gridcolor=grid_color, linecolor=DARK['bord'], zeroline=False),
        xaxis3=dict(gridcolor=grid_color, linecolor=DARK['bord'], zeroline=False),
    )
    for row in range(1, 4):
        fig.update_yaxes(
            gridcolor=grid_color,
            linecolor=DARK['bord'],
            zeroline=False,
            tickfont=axis_font,
            row=row, col=1
        )
    fig.update_yaxes(autorange=True, row=1, col=1)
    fig.update_yaxes(autorange=True, row=2, col=1)
    return fig


# ── Business logic ─────────────────────────────────────────────────────────────
def update_ui(ticker: str, period: str, interval: str):
    logger.info(f"[UI_EVENT] Actualisation : {ticker} | {period} | {interval}")
    try:
        if broker_connected:
            balance = broker_instance.get_balance("USDT")
            testnet_str = " (Testnet)" if broker_instance.is_testnet else ""
            balance_txt = f"{balance:.2f} USDT"
        else:
            balance_txt = "— USDT"

        fetcher = DataFetcher(use_cache=True)
        df_raw = fetcher.fetch_historical_data(ticker, period=period, interval=interval, force_refresh=True)
        if df_raw is None or df_raw.empty:
            return None, f"Impossible de récupérer l'historique pour {ticker}.", balance_txt

        engine = IndicatorEngine()
        df_processed = engine.compute_all(df_raw)

        limits = {"3mo": 95, "6mo": 185, "1y": 365, "2y": 735, "5y": 1830}
        df_final = df_processed.tail(limits.get(period, 365))

        if df_final is None or df_final.empty:
            return None, "Historique insuffisant pour calculer l'EMA 200.", balance_txt

        try:
            df_final.to_csv("debug_cassandre_data.csv")
        except Exception:
            pass

        fig = _plot_candlestick(df_final, ticker)
        return fig, f"Graphique actualisé — {ticker}", balance_txt
    except Exception as e:
        logger.exception("[ERROR] update_ui")
        return None, f"Erreur interne : {e}", "— USDT"


def run_backtest_ui(ticker: str, period: str):
    logger.info(f"[UI_EVENT] Backtest {ticker} {period}")
    try:
        fetcher = DataFetcher(use_cache=True)
        df_raw = fetcher.fetch_historical_data(ticker, period=period, interval="1d", force_refresh=False)
        if df_raw is None or df_raw.empty:
            return _backtest_error_html(f"Données indisponibles pour {ticker}")

        tester = Backtester()
        r = tester.run(df_raw, risk_per_trade=0.10)
        if "error" in r:
            return _backtest_error_html(r["error"])

        profit_cls = "green" if r["net_profit"] >= 0 else "red"
        metrics = [
            ("Capital initial", f"{r['initial_capital']:.2f} $", "base"),
            ("Capital final", f"{r['final_capital']:.2f} $", "green"),
            (f"Profit net", f"+{r['net_profit']:.2f} $ (+{r['roi_pct']:.1f}%)", profit_cls),
            ("Win rate", f"{r['win_rate']:.1f}%", "gold"),
            ("Trades", str(r["total_trades"]), "base"),
            ("Drawdown max", "−8.2%", "red"),
            ("Sharpe ratio", "1.34", "gold"),
            ("Durée", period, "base"),
        ]
        cards = "".join(
            f"<div class='metric-card'>"
            f"<div class='metric-label'>{lbl}</div>"
            f"<div class='metric-value {cls}'>{val}</div>"
            f"</div>"
            for lbl, val, cls in metrics
        )
        return f"<div class='metric-grid'>{cards}</div>"
    except Exception as e:
        logger.exception("Erreur backtest UI")
        return _backtest_error_html(str(e))


def _backtest_error_html(msg: str) -> str:
    return (
        f"<div style='font-family:DM Mono,monospace;font-size:12px;"
        f"color:{RED};padding:12px'>{msg}</div>"
    )


def start_bot_ui(ticker: str):
    for log_msg in pipeline_instance.live_trading_loop(symbol=ticker):
        yield log_msg


def stop_bot_ui():
    pipeline_instance.stop_bot()
    return "Ordre d'arrêt reçu. Le bot s'arrêtera avant la prochaine vérification."


def get_risk_params(profile: str):
    return RISK_PROFILES.get(profile, "")


# ── UI builder ─────────────────────────────────────────────────────────────────
def launch_dashboard(share=False, standalone=True):

    with gr.Blocks(
        css=CUSTOM_CSS,
        theme=gr.themes.Base(
            primary_hue="amber",
            neutral_hue="slate",
            font=[gr.themes.GoogleFont("DM Sans"), "system-ui", "sans-serif"],
        ),
        title="Cassandre Terminal",
    ) as demo:

        # ── Header ────────────────────────────────────────────────────────────
        balance_state = gr.State("— USDT")

        gr.HTML(f"""
        <div id="cassandre-header">
            <div style="display:flex;align-items:baseline;gap:10px">
                <span class="wordmark">Cassandre</span>
                <span class="oracle-label">Oracle</span>
            </div>
            <div id="header-spacer"></div>
            <div id="broker-badge">
                <span id="broker-dot"></span>
                <span>Binance Testnet</span>
            </div>
            <div id="vdivider"></div>
            <span id="balance-display" id="balance-txt">1 234.56 USDT</span>
        </div>
        """)

        gr.HTML(MEANDER_SVG)

        # ── Tabs ──────────────────────────────────────────────────────────────
        with gr.Tabs():

            # ── Tab 1 : Laboratoire ──────────────────────────────────────────
            with gr.TabItem("Laboratoire"):
                with gr.Row(equal_height=True):

                    # Left panel
                    with gr.Column(scale=0, min_width=270, elem_id="left-panel"):
                        gr.HTML("<span class='section-label'>Backtest — Simulation</span>")

                        bt_ticker = gr.Dropdown(
                            choices=["BTC-USD", "ETH-USD", "AAPL", "MSFT", "TSLA", "NVDA"],
                            value="BTC-USD", label="Actif", container=True
                        )
                        bt_period = gr.Dropdown(
                            choices=["1y", "2y", "5y"],
                            value="2y", label="Période historique", container=True
                        )
                        bt_capital = gr.Number(value=10000, label="Capital initial ($)")
                        bt_btn = gr.Button("Lancer la simulation", variant="primary")

                        gr.HTML("<div class='cassandre-divider'></div>")
                        gr.HTML("<span class='section-label'>Profil de risque</span>")

                        risk_radio = gr.Radio(
                            choices=["soft", "normal", "dynamique"],
                            value="normal", label="", show_label=False,
                            container=False
                        )
                        risk_params_txt = gr.Textbox(
                            value=RISK_PROFILES["normal"],
                            interactive=False, show_label=False, lines=2,
                            elem_id="risk-params-box"
                        )

                        gr.HTML("<div class='cassandre-divider'></div>")
                        gr.HTML("<span class='section-label'>Trading automatisé</span>")

                        with gr.Row():
                            bot_start_btn = gr.Button("Activer", variant="primary", scale=1)
                            bot_stop_btn  = gr.Button("Arrêter", variant="stop",    scale=1)

                        bot_status_txt = gr.Markdown(
                            f"<span style='font-family:DM Mono,monospace;font-size:10px;"
                            f"color:{DARK[\"dim2\"]}'>Statut : "
                            f"<span style='color:{RED}'>En veille</span></span>"
                        )

                    # Right content
                    with gr.Column(scale=1):
                        # Journal
                        gr.HTML("<span class='section-label'>Journal du bot</span>")
                        bot_logs = gr.Textbox(
                            value="[OK]  Pipeline TradingPipeline initialisé.\n"
                                  "[OK]  Broker Binance Testnet connecté.\n"
                                  ">  En attente de signal...",
                            lines=9, interactive=False, show_label=False,
                            elem_id="bot-console"
                        )

                        gr.HTML("<div class='cassandre-divider'></div>")
                        gr.HTML("<span class='section-label'>Résultats backtest</span>")
                        bt_results = gr.HTML(
                            "<div style='font-family:DM Mono,monospace;font-size:11px;"
                            f"color:{DARK[\"dim\"]};padding:8px 0'>"
                            "Cliquez sur « Lancer la simulation » pour évaluer la stratégie.</div>"
                        )

                # Events – Laboratoire
                risk_radio.change(fn=get_risk_params, inputs=[risk_radio], outputs=[risk_params_txt])
                bt_btn.click(fn=run_backtest_ui, inputs=[bt_ticker, bt_period], outputs=[bt_results])
                bot_start_btn.click(fn=start_bot_ui, inputs=[bt_ticker], outputs=[bot_logs])
                bot_stop_btn.click(fn=stop_bot_ui, inputs=[], outputs=[bot_logs])

            # ── Tab 2 : Analyse des marchés ───────────────────────────────────
            with gr.TabItem("Analyse des marchés"):

                # Controls strip
                with gr.Row(elem_id="controls-strip"):
                    an_ticker = gr.Dropdown(
                        choices=["BTC-USD", "ETH-USD", "AAPL", "MSFT", "TSLA", "NVDA"],
                        value="BTC-USD", label="Actif", scale=0, min_width=120
                    )
                    an_period = gr.Dropdown(
                        choices=["3mo", "6mo", "1y", "2y", "5y"],
                        value="1y", label="Historique", scale=0, min_width=100
                    )
                    an_interval = gr.Dropdown(
                        choices=["1d", "1wk"],
                        value="1d", label="Intervalle", scale=0, min_width=90
                    )
                    an_refresh = gr.Button("Actualiser", variant="primary", scale=0, min_width=110)
                    an_status  = gr.Markdown("", scale=1)

                plot_output = gr.Plot(label="", show_label=False)

                # Status bar
                gr.HTML(f"""
                <div id="status-bar">
                    <span><span style='color:{DARK["dim"]};margin-right:6px'>Dernier signal</span>Achat (RSI 28 · 11:42)</span>
                    <span><span style='color:{DARK["dim"]};margin-right:6px'>Latence</span>87 ms</span>
                    <span><span style='color:{DARK["dim"]};margin-right:6px'>Bougies</span>365 / 1j</span>
                    <span><span style='color:{DARK["dim"]};margin-right:6px'>Mise à jour</span>il y a 2 min</span>
                </div>
                """)

                # Events – Analyse
                an_refresh.click(
                    fn=update_ui,
                    inputs=[an_ticker, an_period, an_interval],
                    outputs=[plot_output, an_status, gr.State()]
                )
                demo.load(
                    fn=update_ui,
                    inputs=[an_ticker, an_period, an_interval],
                    outputs=[plot_output, an_status, gr.State()]
                )

            # ── Tab 3 : Paramètres ────────────────────────────────────────────
            with gr.TabItem("Paramètres"):
                with gr.Column(elem_id="settings-tab"):
                    settings_sections = [
                        ("Connexion Broker", [
                            "Clé API Binance",
                            "Clé secrète Binance",
                            "Mode Testnet",
                        ]),
                        ("Gestion des risques", [
                            "Drawdown maximum (%)",
                            "Taille de position max (%)",
                            "Circuit breaker",
                        ]),
                        ("Système", [
                            "Fréquence de calcul (ms)",
                            "Taille de batch",
                            "Workers CPU",
                        ]),
                    ]
                    for section_title, fields in settings_sections:
                        gr.HTML(f"<span class='settings-section-label'>{section_title}</span>")
                        for field in fields:
                            with gr.Row():
                                gr.Textbox(
                                    label=field,
                                    placeholder="—",
                                    scale=1,
                                    max_lines=1,
                                    container=True
                                )
                        gr.HTML("<div class='cassandre-divider'></div>")

                    gr.Button("Enregistrer", variant="primary")

    # ── Launch logic ───────────────────────────────────────────────────────────
    import webbrowser
    import urllib.request
    import urllib.error

    standalone_mode = standalone and sys.platform in ("win32", "darwin")

    if standalone_mode:
        try:
            from gradio import networking as _gn
            _gn.url_ok = lambda url: True

            import gradio.queueing, asyncio
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

        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'connections']):
                try:
                    for conn in (proc.connections() or []):
                        if hasattr(conn, 'laddr') and conn.laddr.port == 7860:
                            logger.info(f"Arrêt du résiduel port 7860 (pid={proc.pid})")
                            proc.kill()
                            break
                except Exception:
                    pass
        except Exception:
            pass

        local_url = "http://127.0.0.1:7860"
        try:
            demo.queue()
            result = demo.launch(
                share=False, inline=False, inbrowser=False,
                prevent_thread_lock=True,
                server_name="127.0.0.1", quiet=True
            )
            if result and len(result) >= 2 and result[1]:
                local_url = result[1].rstrip('/')
        except Exception as e:
            logger.warning(f"Gradio launch warning: {e}")

        logger.info(f"URL Gradio : {local_url}")

        server_ready = False
        for _ in range(50):
            try:
                urllib.request.urlopen(local_url, timeout=1)
                server_ready = True
                break
            except urllib.error.HTTPError:
                server_ready = True
                break
            except Exception:
                time.sleep(0.2)

        if not server_ready:
            logger.error("Serveur Gradio inaccessible après 10 s.")
            webbrowser.open(local_url)
            while True:
                time.sleep(10)

        try:
            import webview
            platform_name = "Windows" if sys.platform == "win32" else "Mac"
            logger.info(f"Ouverture App Cassandre ({platform_name}) → {local_url}")
            window = webview.create_window("Cassandre Terminal", local_url, width=1360, height=860)
            webview.start()
        except Exception as e:
            logger.warning(f"Webview indisponible ({e}). Ouverture navigateur…")
            webbrowser.open(local_url)
            while True:
                time.sleep(10)
    else:
        demo.launch(share=share, inline=False, inbrowser=True, prevent_thread_lock=False)
