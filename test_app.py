# test_app.py — Bizon Hardware Tester (standalone, no external imports from src/)
import sys
import subprocess
import importlib.util
import json
import platform
import tkinter as tk
from tkinter import scrolledtext, font


# ─── Auto-install psutil if missing ─────────────────────────────────────────
def ensure_psutil():
    if importlib.util.find_spec("psutil") is None:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])


# ─── Hardware detection (embedded — no src/ import needed) ──────────────────
def detect_hardware():
    import psutil

    # OS
    os_info = {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor() or "Apple Silicon / Unknown",
    }

    # CPU
    freq_mhz = "N/A"
    try:
        f = psutil.cpu_freq()
        if f and f.current > 0:
            freq_mhz = round(f.current, 1)
        elif platform.system() == "Darwin":
            out = subprocess.check_output(["sysctl", "-n", "hw.cpufrequency"],
                                          stderr=subprocess.DEVNULL).decode().strip()
            freq_mhz = round(int(out) / 1e6, 1)
    except Exception:
        pass

    cpu_info = {
        "cores_physical": psutil.cpu_count(logical=False),
        "cores_logical": psutil.cpu_count(logical=True),
        "frequency_mhz": freq_mhz,
        "cpu_percent": psutil.cpu_percent(interval=0.5),
    }

    # RAM
    vm = psutil.virtual_memory()
    ram_info = {
        "total_gb": round(vm.total / 1024**3, 2),
        "available_gb": round(vm.available / 1024**3, 2),
        "percent_used": vm.percent,
    }

    # GPU (torch optional)
    gpu_info = {"device": "CPU (no GPU detected)", "details": None}
    try:
        import torch
        if torch.cuda.is_available():
            gpu_info = {"device": "CUDA (NVIDIA GPU)", "details": torch.cuda.get_device_name(0)}
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            gpu_info = {"device": "MPS (Apple Silicon GPU)", "details": "Metal Performance Shaders"}
    except ImportError:
        gpu_info["details"] = "torch non installé — GPU non vérifié"

    # Python
    py_info = {
        "version": sys.version.split(" ")[0],
        "executable": sys.executable,
    }

    # Adaptation profile
    ram_gb = ram_info["total_gb"]
    gpu = gpu_info["device"]
    cores = cpu_info["cores_physical"] or 2

    if "CUDA" in gpu or "MPS" in gpu:
        batch, freq = 64, 50
    elif ram_gb >= 8:
        batch, freq = 32, 100
    else:
        batch, freq = 16, 200

    adaptation = {
        "batch_size": batch,
        "calc_frequency_ms": freq,
        "workers": max(1, cores - 1),
        "mode": "GPU accéléré" if ("CUDA" in gpu or "MPS" in gpu) else "CPU seul",
    }

    return {
        "os": os_info,
        "cpu": cpu_info,
        "ram": ram_info,
        "gpu": gpu_info,
        "python": py_info,
        "adaptation_bizon": adaptation,
    }


# ─── GUI ─────────────────────────────────────────────────────────────────────
DARK_BG    = "#0d1117"
CARD_BG    = "#161b22"
ACCENT     = "#00d4aa"
ACCENT2    = "#00a8ff"
TEXT_MAIN  = "#e6edf3"
TEXT_DIM   = "#8b949e"
BTN_HOVER  = "#00b890"
ERROR_CLR  = "#ff4d4d"


def run_detection(output_widget, btn, status_lbl):
    btn.config(state=tk.DISABLED, text="🔍 Analyse en cours...")
    status_lbl.config(text="Analyse du matériel...", fg=ACCENT)
    output_widget.config(state=tk.NORMAL)
    output_widget.delete(1.0, tk.END)
    output_widget.update()

    try:
        ensure_psutil()
        report = detect_hardware()

        # Pretty print
        lines = []
        lines.append("╔══════════════════════════════════════╗")
        lines.append("║      BIZON — Rapport Matériel        ║")
        lines.append("╚══════════════════════════════════════╝\n")

        def section(title, data):
            lines.append(f"▶ {title}")
            lines.append("─" * 40)
            for k, v in data.items():
                lines.append(f"  {k:<22} {v}")
            lines.append("")

        section("Système d'exploitation", report["os"])
        section("CPU", report["cpu"])
        section("RAM", report["ram"])
        section("GPU / Accélérateur", report["gpu"])
        section("Python", report["python"])
        section("Profil Bizon adapté", report["adaptation_bizon"])

        lines.append("─" * 40)
        lines.append("✅ Détection terminée avec succès.")

        output_widget.insert(tk.END, "\n".join(lines))
        status_lbl.config(text="✅ Détection terminée", fg=ACCENT)

    except Exception as e:
        output_widget.insert(tk.END, f"❌ Erreur : {e}")
        status_lbl.config(text="❌ Erreur pendant la détection", fg=ERROR_CLR)

    output_widget.config(state=tk.DISABLED)
    btn.config(state=tk.NORMAL, text="🚀 Lancer la Détection")


def main():
    root = tk.Tk()
    root.title("Bizon — Test Matériel")
    root.geometry("680x620")
    root.resizable(False, False)
    root.configure(bg=DARK_BG)

    # ── Header ──
    header = tk.Frame(root, bg=DARK_BG)
    header.pack(fill=tk.X, padx=25, pady=(25, 5))

    title_font = font.Font(family="Helvetica", size=20, weight="bold")
    sub_font   = font.Font(family="Helvetica", size=11)
    mono_font  = font.Font(family="Courier", size=11)
    btn_font   = font.Font(family="Helvetica", size=13, weight="bold")
    small_font = font.Font(family="Helvetica", size=10)

    tk.Label(header, text="🦬 Bizon", font=title_font, fg=ACCENT, bg=DARK_BG).pack(anchor="w")
    tk.Label(header, text="Détection locale du matériel & adaptation des paramètres",
             font=sub_font, fg=TEXT_DIM, bg=DARK_BG).pack(anchor="w")

    # ── Divider ──
    tk.Frame(root, height=1, bg=ACCENT, bd=0).pack(fill=tk.X, padx=25, pady=8)

    # ── Status label ──
    status_lbl = tk.Label(root, text="En attente…", font=small_font, fg=TEXT_DIM, bg=DARK_BG)
    status_lbl.pack(anchor="w", padx=25)

    # ── Button ──
    btn_frame = tk.Frame(root, bg=DARK_BG)
    btn_frame.pack(fill=tk.X, padx=25, pady=10)

    btn = tk.Button(
        btn_frame,
        text="🚀 Lancer la Détection",
        font=btn_font,
        bg=ACCENT, fg="#0d1117",
        activebackground=BTN_HOVER,
        relief=tk.FLAT,
        padx=20, pady=10,
        cursor="hand2",
        bd=0,
    )
    btn.pack(side=tk.LEFT)
    btn.config(command=lambda: run_detection(output_txt, btn, status_lbl))

    # ── Output text area ──
    output_frame = tk.Frame(root, bg=CARD_BG, bd=0)
    output_frame.pack(fill=tk.BOTH, expand=True, padx=25, pady=(0, 20))

    output_txt = scrolledtext.ScrolledText(
        output_frame,
        font=mono_font,
        bg=CARD_BG,
        fg=TEXT_MAIN,
        insertbackground=TEXT_MAIN,
        relief=tk.FLAT,
        padx=14,
        pady=10,
        wrap=tk.NONE,
        state=tk.DISABLED,
    )
    output_txt.pack(fill=tk.BOTH, expand=True)
    output_txt.config(state=tk.NORMAL)
    output_txt.insert(tk.END, "Cliquez sur le bouton ci-dessus pour analyser cette machine.\n"
                              "psutil sera installé automatiquement si absente.")
    output_txt.config(state=tk.DISABLED)

    # ── Footer ──
    tk.Label(root, text="Projet Olympus — Module Bizon · ECE Paris 2026",
             font=small_font, fg=TEXT_DIM, bg=DARK_BG).pack(pady=(0, 8))

    root.mainloop()


if __name__ == "__main__":
    main()
