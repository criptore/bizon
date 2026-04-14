# test_app.py — Bizon Hardware Tester
# Standalone, cross-platform (Mac & Windows)
# Auto-installs: psutil, torch on first click
import sys
import subprocess
import importlib.util
import platform
import threading
import tkinter as tk
from tkinter import scrolledtext, font


# ─── Dependency installer ────────────────────────────────────────────────────

DEPS = ["psutil", "torch"]


def is_installed(pkg):
    """Check if a package is importable."""
    return importlib.util.find_spec(pkg) is not None


def get_torch_install_cmd():
    """
    Return the right pip command to install torch depending on platform.
    - Windows + NVIDIA GPU → CUDA build
    - Mac arm64            → default (includes MPS support)
    - Everything else      → CPU-only build (smaller, faster to download)
    """
    system = platform.system()

    if system == "Windows":
        try:
            result = subprocess.run(
                ["nvidia-smi"], capture_output=True, timeout=5
            )
            if result.returncode == 0:
                return [
                    sys.executable, "-m", "pip", "install", "--quiet",
                    "torch",
                    "--index-url", "https://download.pytorch.org/whl/cu121"
                ]
        except Exception:
            pass
        return [
            sys.executable, "-m", "pip", "install", "--quiet",
            "torch",
            "--index-url", "https://download.pytorch.org/whl/cpu"
        ]

    return [sys.executable, "-m", "pip", "install", "--quiet", "torch"]


def install_dependencies(log_fn):
    """Install missing packages, calling log_fn(msg) for progress updates."""
    missing = [p for p in DEPS if not is_installed(p)]

    if not missing:
        log_fn("✅ Toutes les dépendances sont déjà installées.\n")
        return True

    for pkg in missing:
        log_fn(f"📦 Installation de {pkg}...")
        try:
            if pkg == "torch":
                cmd = get_torch_install_cmd()
            else:
                cmd = [sys.executable, "-m", "pip", "install", "--quiet", pkg]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                log_fn(f"   ✅ {pkg} installé avec succès.\n")
            else:
                log_fn(f"   ❌ Erreur lors de l'installation de {pkg}:\n{result.stderr}\n")
                return False
        except subprocess.TimeoutExpired:
            log_fn(f"   ❌ Timeout — installation de {pkg} trop longue.\n")
            return False
        except Exception as e:
            log_fn(f"   ❌ {e}\n")
            return False

    return True


# ─── Hardware detection ───────────────────────────────────────────────────────

def detect_hardware(log_fn):
    import psutil

    log_fn("\n  Analyse du matériel en cours…\n")

    os_info = {
        "system":    platform.system(),
        "release":   platform.release(),
        "machine":   platform.machine(),
        "processor": platform.processor() or "Apple Silicon / Unknown",
    }

    freq_mhz = "N/A"
    try:
        f = psutil.cpu_freq()
        if f and f.current > 0:
            freq_mhz = round(f.current, 1)
        elif platform.system() == "Darwin":
            out = subprocess.check_output(
                ["sysctl", "-n", "hw.cpufrequency"], stderr=subprocess.DEVNULL
            ).decode().strip()
            freq_mhz = round(int(out) / 1e6, 1)
    except Exception:
        pass

    cpu_info = {
        "cores_physical": psutil.cpu_count(logical=False),
        "cores_logical":  psutil.cpu_count(logical=True),
        "frequency_mhz":  freq_mhz,
        "cpu_percent":    psutil.cpu_percent(interval=0.5),
    }

    vm = psutil.virtual_memory()
    ram_info = {
        "total_gb":     round(vm.total / 1024**3, 2),
        "available_gb": round(vm.available / 1024**3, 2),
        "percent_used": vm.percent,
    }

    gpu_info = {"device": "CPU (aucun GPU détecté)", "details": None}
    try:
        import importlib
        torch = importlib.import_module("torch")
        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            vram = round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 1)
            gpu_info = {
                "device":       f"CUDA — {name}",
                "vram_gb":      vram,
                "cuda_version": torch.version.cuda,
            }
            log_fn(f"   GPU NVIDIA détecté : {name}\n")
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            gpu_info = {
                "device":  "MPS — Apple Silicon GPU",
                "details": "Metal Performance Shaders (GPU intégré)",
            }
            log_fn("   GPU Apple Silicon (MPS) détecté\n")
        else:
            log_fn("   Aucun GPU compatible détecté (CUDA ou MPS)\n")
    except Exception as e:
        gpu_info["details"] = f"torch importé mais erreur : {e}"

    py_info = {
        "version":    sys.version.split(" ")[0],
        "executable": sys.executable,
    }

    ram_gb = ram_info["total_gb"]
    gpu    = gpu_info["device"]
    cores  = cpu_info["cores_physical"] or 2

    if "CUDA" in gpu or "MPS" in gpu:
        batch, freq = 64, 50
    elif ram_gb >= 8:
        batch, freq = 32, 100
    else:
        batch, freq = 16, 200

    adaptation = {
        "batch_size":       batch,
        "calc_frequency_ms": freq,
        "workers":          max(1, cores - 1),
        "mode":             "GPU accéléré" if ("CUDA" in gpu or "MPS" in gpu) else "CPU seul",
    }

    return {
        "os":              os_info,
        "cpu":             cpu_info,
        "ram":             ram_info,
        "gpu":             gpu_info,
        "python":          py_info,
        "adaptation_bizon": adaptation,
    }


def format_report(report):
    lines = []
    lines.append("  ─────────────────────────────────────────")
    lines.append("    BIZON — Rapport Matériel")
    lines.append("  ─────────────────────────────────────────\n")

    labels = {
        "os":               "Système d'exploitation",
        "cpu":              "Processeur",
        "ram":              "Mémoire RAM",
        "gpu":              "GPU / Accélérateur",
        "python":           "Python",
        "adaptation_bizon": "Profil Bizon adapté",
    }

    for key, title in labels.items():
        data = report.get(key, {})
        lines.append(f"  ▸ {title}")
        lines.append("  " + "·" * 40)
        if isinstance(data, dict):
            for k, v in data.items():
                lines.append(f"    {k:<26} {v}")
        else:
            lines.append(f"    {data}")
        lines.append("")

    lines.append("  ─────────────────────────────────────────")
    lines.append("  ✅ Détection terminée avec succès.")
    return "\n".join(lines)


# ─── Palette ─────────────────────────────────────────────────────────────────

BG        = "#F5EFE6"   # beige pastel de fond
CARD      = "#EDE0D0"   # carte légèrement plus foncée
BORDER    = "#C8B89A"   # bordure douce
ACCENT    = "#7A4E2D"   # marron foncé bouton
ACCENT_H  = "#5C3820"   # marron très foncé hover
TEXT      = "#2C1A0E"   # texte foncé marron profond
TEXT_DIM  = "#9E8070"   # texte atténué
SUCCESS   = "#4A7A4A"   # vert doux sauge
WARNING   = "#B07A28"   # ambre chaud
ERROR     = "#8E3028"   # rouge terre cuite
BTN_TXT   = "#FFFFFF"   # blanc pur sur bouton


# ─── Helpers ─────────────────────────────────────────────────────────────────

def append(widget, text, color=None):
    """Thread-safe append to ScrolledText."""
    def _do():
        widget.config(state=tk.NORMAL)
        widget.insert(tk.END, text)
        widget.see(tk.END)
        widget.config(state=tk.DISABLED)
    widget.after(0, _do)


def set_status_pill(pill, text, color):
    """Update the canvas-based pill badge."""
    def _do():
        pill.delete("all")
        w = pill.winfo_width() or 200
        h = pill.winfo_height() or 30
        r = h // 2
        _rounded_rect_fill(pill, 0, 0, w, h, r, fill=CARD, outline=BORDER, width=1)
        pill.create_text(w // 2, h // 2, text=text, fill=color,
                         font=pill._font, anchor="center")
    pill.after(0, _do)


def clear(widget):
    def _do():
        widget.config(state=tk.NORMAL)
        widget.delete(1.0, tk.END)
        widget.config(state=tk.DISABLED)
    widget.after(0, _do)


# ─── Canvas drawing primitives ────────────────────────────────────────────────

def _rounded_rect_fill(canvas, x1, y1, x2, y2, r, **kw):
    """Fill a true rounded-rectangle on a Canvas."""
    points = [
        x1+r, y1,
        x2-r, y1,
        x2,   y1,
        x2,   y1+r,
        x2,   y2-r,
        x2,   y2,
        x2-r, y2,
        x1+r, y2,
        x1,   y2,
        x1,   y2-r,
        x1,   y1+r,
        x1,   y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kw)


# ─── Rounded Card widget ──────────────────────────────────────────────────────

class RoundedCard(tk.Canvas):
    """
    A Canvas that draws a rounded rectangle as its background.
    Child widgets are placed via a tk.Frame embedded inside.
    """
    def __init__(self, parent, radius=16, bg_outer=BG, fill=CARD,
                 outline=BORDER, **kwargs):
        super().__init__(parent, bg=bg_outer, highlightthickness=0, bd=0, **kwargs)
        self._radius = radius
        self._fill   = fill
        self._outline = outline
        # Inner frame where to place children
        self.inner = tk.Frame(self, bg=fill, bd=0)
        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, event):
        self.delete("bg")
        w, h = event.width, event.height
        r = self._radius
        _rounded_rect_fill(self, 0, 0, w, h, r,
                           fill=self._fill, outline=self._outline,
                           width=1, tags="bg")
        # Keep inner frame inside with padding
        pad = 1
        self.coords(self.create_window(
            pad, pad,
            anchor="nw",
            window=self.inner,
            width=w - 2*pad,
            height=h - 2*pad,
        ))

    def place_inner(self, **pack_kw):
        """Pack the inner frame and return it for child widget placement."""
        # The inner frame is managed by the canvas window; just return it.
        return self.inner


# ─── Rounded Button widget ────────────────────────────────────────────────────

class RoundedButton:
    """
    A Canvas-based button with true rounded corners.
    Wraps a Canvas instead of inheriting to avoid Tcl initialization bugs.
    """
    def __init__(self, parent, text="", command=None, font_obj=None,
                 radius=22, fill=ACCENT, fill_hover=ACCENT_H,
                 text_color=BTN_TXT, bg_outer=BG,
                 pad_x=32, pad_y=14, **kwargs):

        self.parent = parent
        
        if font_obj is not None:
            tw = font_obj.measure(text)
            th = font_obj.metrics("linespace")
        else:
            tw, th = 160, 20

        self._w = tw + pad_x * 2
        self._h = th + pad_y * 2
        
        # Container frame
        self.frame = tk.Frame(parent, bg=bg_outer, bd=0)
        
        # Actual drawing canvas
        self.canvas = tk.Canvas(self.frame, width=self._w, height=self._h, 
                                bg=bg_outer, highlightthickness=0, bd=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self._fill       = fill
        self._fill_hover = fill_hover
        self._text_color = text_color
        self._text       = text
        self._font       = font_obj
        self._command    = command
        self._radius     = radius
        self._disabled   = False
        self._ready      = False

        self.canvas.bind("<Configure>", self._on_configure)
        self.canvas.bind("<Enter>",          self._on_enter)
        self.canvas.bind("<Leave>",          self._on_leave)
        self.canvas.bind("<ButtonPress-1>",  self._on_press)
        self.canvas.bind("<ButtonRelease-1>",self._on_release)
        
    def pack(self, **kwargs):
        self.frame.pack(**kwargs)
        
    def grid(self, **kwargs):
        self.frame.grid(**kwargs)
        
    def place(self, **kwargs):
        self.frame.place(**kwargs)

    def _on_configure(self, event):
        if not self._ready:
            self._ready = True
            self._draw(self._fill)

    def _draw(self, bg_color):
        self.canvas.delete("all")
        r = self._radius
        w, h = self._w, self._h
        _rounded_rect_fill(self.canvas, 0, 0, w, h, r,
                           fill=bg_color, outline="", tags="btn")
        self.canvas.create_text(w // 2, h // 2, text=self._text,
                         fill=self._text_color, font=self._font,
                         anchor="center", tags="lbl")

    def _on_enter(self, _):
        if not self._disabled:
            self._draw(self._fill_hover)
            self.canvas.config(cursor="hand2")

    def _on_leave(self, _):
        if not self._disabled:
            self._draw(self._fill)

    def _on_press(self, _):
        if not self._disabled:
            self._draw(self._fill_hover)

    def _on_release(self, _):
        if not self._disabled:
            self._draw(self._fill)
            if self._command:
                self._command()

    def set_text(self, text):
        self._text = text
        if self._ready:
            self._draw(self._fill)

    def set_disabled(self, disabled: bool):
        self._disabled = disabled
        if self._ready:
            col = "#C0A88A" if disabled else self._fill
            self._draw(col)
        self.canvas.config(cursor="" if disabled else "hand2")
        
    def after(self, ms, func=None, *args):
        return self.canvas.after(ms, func, *args)


# ─── Pipeline ────────────────────────────────────────────────────────────────

class AppState:
    """Mutable references shared between GUI and pipeline thread."""
    def __init__(self):
        self.btn        = None
        self.output_txt = None
        self.pill       = None


def run_pipeline(state: AppState):
    """Full pipeline: install deps → detect hardware. Runs in a thread."""
    clear(state.output_txt)
    set_status_pill(state.pill, "Vérification des dépendances…", WARNING)
    state.btn.after(0, lambda: state.btn.set_disabled(True))
    state.btn.after(0, lambda: state.btn.set_text("En cours…"))

    def log(msg):
        append(state.output_txt, msg)

    log("  ══════════════════════════════════════\n")
    log("    Bizon  ·  Initialisation\n")
    log("  ══════════════════════════════════════\n\n")

    log("  Vérification des dépendances…\n")
    ok = install_dependencies(log)

    if not ok:
        set_status_pill(state.pill, "Erreur d'installation", ERROR)
        state.btn.after(0, lambda: state.btn.set_disabled(False))
        state.btn.after(0, lambda: state.btn.set_text("Lancer la détection"))
        return

    set_status_pill(state.pill, "Analyse du matériel…", WARNING)
    try:
        report = detect_hardware(log)
        log("\n")
        log(format_report(report))
        set_status_pill(state.pill, "Détection terminée avec succès", SUCCESS)
    except Exception as e:
        log(f"\n  Erreur lors de la détection : {e}\n")
        set_status_pill(state.pill, "Erreur lors de la détection", ERROR)

    state.btn.after(0, lambda: state.btn.set_disabled(False))
    state.btn.after(0, lambda: state.btn.set_text("Lancer la détection"))


# ─── GUI ─────────────────────────────────────────────────────────────────────

def main():
    root = tk.Tk()
    root.title("Bizon")
    root.geometry("740x700")
    root.resizable(True, True)
    root.configure(bg=BG)
    root.minsize(620, 540)

    # ── Fonts
    FAMILY = "Acumin Wide"
    title_font = font.Font(family=FAMILY, size=22, weight="bold")
    sub_font   = font.Font(family=FAMILY, size=11)
    mono_font  = font.Font(family=FAMILY, size=10)
    btn_font   = font.Font(family=FAMILY, size=13, weight="bold")
    small_font = font.Font(family=FAMILY, size=9)
    lbl_font   = font.Font(family=FAMILY, size=10)
    pill_font  = font.Font(family=FAMILY, size=10)

    # ── Outer padding wrapper
    outer = tk.Frame(root, bg=BG)
    outer.pack(fill=tk.BOTH, expand=True, padx=28, pady=24)

    # ────────────────────────────────────────────
    # HEADER CARD — true rounded via RoundedCard
    # ────────────────────────────────────────────
    header_canvas = tk.Canvas(outer, bg=BG, highlightthickness=0, height=100)
    header_canvas.pack(fill=tk.X, pady=(0, 14))

    # We draw the card lazily after the canvas is mapped
    _header_rect_id = [None]

    def _draw_header(event=None):
        header_canvas.delete("all")
        w = header_canvas.winfo_width()
        h = header_canvas.winfo_height()
        _rounded_rect_fill(header_canvas, 0, 0, w, h, 18,
                           fill=CARD, outline=BORDER, width=1)
        # Title
        header_canvas.create_text(
            24, h // 2 - 14,
            text="Bizon", anchor="w",
            font=title_font, fill=ACCENT
        )
        header_canvas.create_text(
            24 + title_font.measure("Bizon") + 10, h // 2 - 10,
            text="· Test Matériel", anchor="w",
            font=sub_font, fill=TEXT_DIM
        )
        header_canvas.create_text(
            24, h // 2 + 14,
            text="Détection locale du matériel & adaptation des paramètres",
            anchor="w", font=sub_font, fill=TEXT_DIM
        )

    header_canvas.bind("<Configure>", _draw_header)

    # ── Separator
    tk.Frame(outer, height=1, bg=BORDER).pack(fill=tk.X, pady=(0, 14))

    # ────────────────────────────────────────────
    # STATUS ROW — pill badge
    # ────────────────────────────────────────────
    status_row = tk.Frame(outer, bg=BG)
    status_row.pack(fill=tk.X, pady=(0, 12))

    tk.Label(status_row, text="Statut",
             font=lbl_font, fg=TEXT_DIM, bg=BG).pack(side=tk.LEFT, padx=(2, 8))

    pill = tk.Canvas(status_row, bg=BG, highlightthickness=0,
                     width=220, height=30)
    pill._font = pill_font
    pill.pack(side=tk.LEFT)

    def _draw_pill(text, color):
        pill.delete("all")
        w, h = 220, 30
        _rounded_rect_fill(pill, 0, 0, w, h, h // 2,
                           fill=CARD, outline=BORDER, width=1)
        pill.create_text(w // 2, h // 2, text=text, fill=color,
                         font=pill_font, anchor="center")

    _draw_pill("En attente…", TEXT_DIM)

    # Monkey-patch so set_status_pill can call it
    pill._draw_pill = _draw_pill

    def _set_status(text, color):
        pill.after(0, lambda: _draw_pill(text, color))

    # ────────────────────────────────────────────
    # ROUNDED BUTTON
    # ────────────────────────────────────────────
    btn_row = tk.Frame(outer, bg=BG)
    btn_row.pack(fill=tk.X, pady=(0, 14))

    state = AppState()

    # Ensure all parent frames are registered with Tk before creating Canvas child
    root.update_idletasks()

    btn = RoundedButton(
        btn_row,
        text="Lancer la détection",
        font_obj=btn_font,
        radius=22,
        fill=ACCENT,
        fill_hover=ACCENT_H,
        text_color=BTN_TXT,
        bg_outer=BG,
        pad_x=32, pad_y=13,
    )
    btn.pack(side=tk.LEFT)


    # ────────────────────────────────────────────
    # OUTPUT CARD — rounded via Canvas
    # ────────────────────────────────────────────
    out_canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
    out_canvas.pack(fill=tk.BOTH, expand=True, pady=(0, 14))

    out_inner = tk.Frame(out_canvas, bg=CARD, bd=0)

    _out_win = out_canvas.create_window(0, 0, anchor="nw", window=out_inner)

    def _draw_out(event=None):
        out_canvas.delete("bg")
        w = out_canvas.winfo_width()
        h = out_canvas.winfo_height()
        _rounded_rect_fill(out_canvas, 0, 0, w, h, 18,
                           fill=CARD, outline=BORDER, width=1, tags="bg")
        out_canvas.tag_lower("bg")
        out_canvas.coords(_out_win, 2, 2)
        out_canvas.itemconfig(_out_win, width=w - 4, height=h - 4)

    out_canvas.bind("<Configure>", _draw_out)

    output_txt = scrolledtext.ScrolledText(
        out_inner,
        font=mono_font,
        bg=CARD, fg=TEXT,
        insertbackground=TEXT,
        selectbackground=BORDER,
        selectforeground=TEXT,
        relief=tk.FLAT,
        padx=20, pady=16,
        wrap=tk.NONE,
        state=tk.DISABLED,
        borderwidth=0,
    )
    output_txt.pack(fill=tk.BOTH, expand=True)

    append(
        output_txt,
        "  Bienvenue dans Bizon · Test Matériel\n\n"
        "  Cliquez sur « Lancer la détection » pour analyser votre configuration.\n"
        "  Les dépendances (psutil, torch) seront installées automatiquement\n"
        "  si elles ne sont pas encore présentes sur votre système.\n"
    )

    # ──  Wire state
    state.btn        = btn
    state.output_txt = output_txt
    state.pill       = pill

    # Patch pill so run_pipeline can call through
    def _pill_set(text, color):
        pill.after(0, lambda: _draw_pill(text, color))
    pill.delete   # no-op trick to verify it's the right object
    # Override module-level: wrap set_status_pill to use our closure
    import types
    def _monkey_set_status(p, text, color):
        p.after(0, lambda: p._draw_pill(text, color))
    globals()["set_status_pill"] = _monkey_set_status

    btn._command = lambda: threading.Thread(
        target=run_pipeline, args=(state,), daemon=True
    ).start()

    # ────────────────────────────────────────────
    # FOOTER
    # ────────────────────────────────────────────
    tk.Label(
        outer,
        text="Projet Olympus  ·  Module Bizon  ·  ECE Paris 2026",
        font=small_font, fg=TEXT_DIM, bg=BG
    ).pack(pady=(0, 4))

    root.mainloop()


if __name__ == "__main__":
    main()
