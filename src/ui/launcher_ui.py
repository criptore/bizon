import tkinter as tk
from tkinter import scrolledtext, font as tkfont
import threading
import logging
from src.hardware.detector import detect_hardware

logger = logging.getLogger("LauncherUI")

# ── Design tokens (Launcher palette) ──────────────────────────────────────────
BG       = "#F7F4EF"
CARD     = "#EDE8DF"
BORDER   = "#D8D0C4"
TEXT     = "#1A1612"
TEXT_DIM = "#8A7F74"
GOLD     = "#B8942A"
SUCCESS  = "#4CAF87"
BTN_BG   = "#1A1612"
BTN_TXT  = "#F7F4EF"

TL_RED   = "#FF6B6B"
TL_YEL   = "#FFC15E"
TL_GRN   = "#6BCB77"

MEANDER_PATH = "M0,6.5 H4 V1.5 H16 V11.5 H12 V6.5 H20"


class _MeanderBar(tk.Canvas):
    """Horizontal meander SVG pattern drawn on a Tk Canvas."""

    def __init__(self, parent, width=620, **kwargs):
        super().__init__(parent, width=width, height=13,
                         bg=BG, highlightthickness=0, **kwargs)
        self._w = width
        self.bind("<Configure>", lambda e: self._draw(e.width))
        self._draw(width)

    def _draw(self, total_width: int):
        self.delete("all")
        color = GOLD
        opacity_hex = "66"  # ~0.40 alpha approximated via colour
        stroke_col = color   # Tk Canvas doesn't support opacity; use solid gold

        # Pattern tile: width=20, height=13
        # Points derived from: M0,6.5 H4 V1.5 H16 V11.5 H12 V6.5 H20
        tile = [(0, 6.5), (4, 6.5), (4, 1.5), (16, 1.5),
                (16, 11.5), (12, 11.5), (12, 6.5), (20, 6.5)]
        tile_w = 20
        tiles = (total_width // tile_w) + 2
        for i in range(tiles):
            pts = [(x + i * tile_w, y) for x, y in tile]
            # draw as polyline segments
            for j in range(len(pts) - 1):
                x0, y0 = pts[j]
                x1, y1 = pts[j + 1]
                self.create_line(x0, y0, x1, y1,
                                 fill=stroke_col, width=1, capstyle=tk.BUTT)


class _OutlineButton(tk.Canvas):
    """Flat outline button with hover invert — matches 'Lancer le Terminal' spec."""

    W, H = 220, 40

    def __init__(self, parent, text="", command=None, font_obj=None):
        super().__init__(parent, width=self.W, height=self.H,
                         bg=BG, highlightthickness=0)
        self._text = text
        self._cmd  = command
        self._font = font_obj
        self.bind("<Enter>",    lambda e: self._draw(hover=True))
        self.bind("<Leave>",    lambda e: self._draw(hover=False))
        self.bind("<Button-1>", lambda e: self._cmd() if self._cmd else None)
        self._draw(hover=False)

    def _draw(self, hover: bool):
        self.delete("all")
        bg_col  = BTN_BG if hover else BG
        txt_col = BTN_TXT if hover else TEXT
        brd_col = BTN_BG
        self.create_rectangle(1, 1, self.W - 1, self.H - 1,
                               outline=brd_col, fill=bg_col, width=2)
        self.create_text(self.W // 2, self.H // 2,
                         text=self._text, fill=txt_col, font=self._font,
                         anchor="center")


class LauncherUI:
    """Cassandre Control Center — Tkinter launcher window (700 × 580)."""

    WIN_W, WIN_H = 700, 580

    def __init__(self, on_launch_callback):
        self.on_launch = on_launch_callback
        self.root = tk.Tk()
        self.root.title("Cassandre Control Center")
        self.root.geometry(f"{self.WIN_W}x{self.WIN_H}")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)
        self._build()

    # ── UI construction ────────────────────────────────────────────────────────
    def _build(self):
        self._setup_fonts()
        self._build_titlebar()
        self._build_header()
        self._build_report()
        self._build_footer()
        threading.Thread(target=self._detect_hardware, daemon=True).start()

    def _setup_fonts(self):
        # Cormorant Garamond isn't bundled — Georgia is the closest serif fallback
        self.font_title = tkfont.Font(family="Georgia", size=28, weight="normal")
        self.font_sub   = tkfont.Font(family="Arial", size=9, weight="normal")
        self.font_mono  = tkfont.Font(family="Courier New", size=11)
        self.font_btn   = tkfont.Font(family="Arial", size=10, weight="bold")
        self.font_label = tkfont.Font(family="Arial", size=8)
        self.font_ver   = tkfont.Font(family="Courier New", size=10)

    # ── Title bar ──────────────────────────────────────────────────────────────
    def _build_titlebar(self):
        bar = tk.Frame(self.root, bg="#EDE8DF", height=30)
        bar.pack(fill=tk.X, side=tk.TOP)
        bar.pack_propagate(False)

        # Traffic lights
        dot_frame = tk.Frame(bar, bg="#EDE8DF")
        dot_frame.pack(side=tk.LEFT, padx=14, pady=9)
        for color in (TL_RED, TL_YEL, TL_GRN):
            c = tk.Canvas(dot_frame, width=12, height=12,
                          bg="#EDE8DF", highlightthickness=0)
            c.pack(side=tk.LEFT, padx=4)
            c.create_oval(1, 1, 11, 11, fill=color, outline="")

        # Title (centred)
        tk.Label(bar, text="Cassandre Control Center",
                 bg="#EDE8DF", fg=TEXT_DIM,
                 font=tkfont.Font(family="Arial", size=10),
                 anchor="center").pack(fill=tk.X, side=tk.LEFT, expand=True, padx=(0, 46))

        # Bottom border
        border = tk.Frame(self.root, bg=BORDER, height=1)
        border.pack(fill=tk.X, side=tk.TOP)

    # ── Wordmark + meander ─────────────────────────────────────────────────────
    def _build_header(self):
        pad = tk.Frame(self.root, bg=BG)
        pad.pack(fill=tk.X, padx=40, pady=(20, 0))

        # "CASSANDRE"
        tk.Label(pad, text="CASSANDRE",
                 font=self.font_title, fg=TEXT, bg=BG,
                 anchor="w").pack(anchor="w")

        # Subtitle
        tk.Label(pad, text="ORACLE DE TRADING ALGORITHMIQUE",
                 font=tkfont.Font(family="Arial", size=9, weight="bold"),
                 fg=GOLD, bg=BG,
                 anchor="w").pack(anchor="w", pady=(2, 10))

        # Meander
        _MeanderBar(pad, width=self.WIN_W - 80).pack(anchor="w", fill=tk.X)

    # ── Report area ────────────────────────────────────────────────────────────
    def _build_report(self):
        self.report = scrolledtext.ScrolledText(
            self.root,
            bg=CARD, fg=TEXT,
            font=self.font_mono,
            relief=tk.FLAT,
            padx=20, pady=16,
            borderwidth=0,
            highlightbackground=BORDER,
            highlightthickness=1,
            wrap=tk.NONE,
        )
        self.report.pack(fill=tk.BOTH, expand=True, padx=40, pady=14)
        self.report.insert(tk.END, "Analyse du matériel en cours…\n")
        self.report.config(state=tk.DISABLED)

    # ── Footer ─────────────────────────────────────────────────────────────────
    def _build_footer(self):
        footer = tk.Frame(self.root, bg=BG)
        footer.pack(fill=tk.X, padx=40, pady=(0, 20))

        # Version label (left)
        tk.Label(footer, text="v 1.0.0",
                 font=self.font_ver, fg=TEXT_DIM, bg=BG).pack(side=tk.LEFT)

        # "Lancer le Terminal" button (right)
        btn = _OutlineButton(footer,
                             text="LANCER LE TERMINAL",
                             command=self._on_launch,
                             font_obj=self.font_btn)
        btn.pack(side=tk.RIGHT)

    # ── Hardware detection ─────────────────────────────────────────────────────
    def _detect_hardware(self):
        logger.info("[HARDWARE] Détection démarrée…")
        try:
            r = detect_hardware()
            lines = [
                "RAPPORT CONFIGURATION",
                "─" * 34,
                f"Système   {r['os']['system']}  ·  {r['os']['machine']}",
                f"CPU       {r['cpu']['cores_logical']} cœurs  ·  {r['cpu']['frequency_mhz']} MHz",
                f"RAM       {r['ram']['total_gb']} Go",
                f"GPU       {r['gpu']['device']}",
                "",
                "PROFIL OPTIMISÉ",
                "─" * 34,
                f"Batch Size        {r['adaptation']['batch_size']}",
                f"Workers            {r['adaptation']['workers']}",
                f"Fréquence       {r['adaptation']['calc_frequency_ms']} ms",
                "",
                "[OK]  Détection matérielle terminée.",
                "[OK]  Mode recommandé : Paper Trading.",
            ]
            text = "\n".join(lines)
            logger.info("[HARDWARE] Détection terminée.")
        except Exception as e:
            logger.error(f"[HARDWARE] Erreur : {e}")
            text = f"Erreur lors de la détection matérielle :\n{e}"

        self.root.after(0, lambda t=text: self._set_report(t))

    def _set_report(self, text: str):
        self.report.config(state=tk.NORMAL)
        self.report.delete(1.0, tk.END)
        self.report.insert(tk.END, text)
        self.report.config(state=tk.DISABLED)

    # ── Callbacks ──────────────────────────────────────────────────────────────
    def _on_launch(self):
        if self.on_launch:
            self.on_launch()

    def run(self):
        self.root.mainloop()

    def close(self):
        self.root.destroy()
