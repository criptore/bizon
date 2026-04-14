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
        # Try to detect an NVIDIA GPU via nvidia-smi
        try:
            result = subprocess.run(
                ["nvidia-smi"], capture_output=True, timeout=5
            )
            if result.returncode == 0:
                # CUDA 12.1 build
                return [
                    sys.executable, "-m", "pip", "install", "--quiet",
                    "torch",
                    "--index-url", "https://download.pytorch.org/whl/cu121"
                ]
        except Exception:
            pass
        # CPU-only Windows
        return [
            sys.executable, "-m", "pip", "install", "--quiet",
            "torch",
            "--index-url", "https://download.pytorch.org/whl/cpu"
        ]

    # macOS or Linux — default pip (includes MPS for Apple Silicon)
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

    log_fn("\n🔍 Analyse du matériel...\n")

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
            out = subprocess.check_output(
                ["sysctl", "-n", "hw.cpufrequency"], stderr=subprocess.DEVNULL
            ).decode().strip()
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

    # GPU — reload torch in case it was just installed
    gpu_info = {"device": "CPU (aucun GPU détecté)", "details": None}
    try:
        import importlib
        torch = importlib.import_module("torch")
        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            vram = round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 1)
            gpu_info = {
                "device": f"CUDA — {name}",
                "vram_gb": vram,
                "cuda_version": torch.version.cuda,
            }
            log_fn(f"   🎮 GPU NVIDIA détecté : {name}\n")
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            gpu_info = {
                "device": "MPS — Apple Silicon GPU",
                "details": "Metal Performance Shaders (GPU intégré)",
            }
            log_fn("   🍎 GPU Apple Silicon (MPS) détecté\n")
        else:
            log_fn("   ℹ️  Aucun GPU compatible détecté (CUDA ou MPS)\n")
    except Exception as e:
        gpu_info["details"] = f"torch importé mais erreur : {e}"

    # Python
    py_info = {
        "version": sys.version.split(" ")[0],
        "executable": sys.executable,
    }

    # Bizon adaptation profile
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


def format_report(report):
    lines = []
    lines.append("╔══════════════════════════════════════╗")
    lines.append("║      BIZON — Rapport Matériel        ║")
    lines.append("╚══════════════════════════════════════╝\n")

    labels = {
        "os": "Système d'exploitation",
        "cpu": "CPU",
        "ram": "RAM",
        "gpu": "GPU / Accélérateur",
        "python": "Python",
        "adaptation_bizon": "Profil Bizon adapté",
    }

    for key, title in labels.items():
        data = report.get(key, {})
        lines.append(f"▶ {title}")
        lines.append("─" * 44)
        if isinstance(data, dict):
            for k, v in data.items():
                lines.append(f"  {k:<24} {v}")
        else:
            lines.append(f"  {data}")
        lines.append("")

    lines.append("─" * 44)
    lines.append("✅ Détection terminée avec succès.")
    return "\n".join(lines)


# ─── GUI ─────────────────────────────────────────────────────────────────────

DARK_BG  = "#0d1117"
CARD_BG  = "#161b22"
ACCENT   = "#00d4aa"
TEXT     = "#e6edf3"
TEXT_DIM = "#8b949e"
BTN_ACT  = "#00b890"
ERR      = "#ff4d4d"
WARN     = "#f0a500"


def append(widget, text, color=None):
    """Thread-safe append to ScrolledText."""
    def _do():
        widget.config(state=tk.NORMAL)
        widget.insert(tk.END, text)
        widget.see(tk.END)
        widget.config(state=tk.DISABLED)
    widget.after(0, _do)


def set_status(lbl, text, color):
    lbl.after(0, lambda: lbl.config(text=text, fg=color))


def set_btn(btn, text, state):
    btn.after(0, lambda: btn.config(text=text, state=state))


def clear(widget):
    def _do():
        widget.config(state=tk.NORMAL)
        widget.delete(1.0, tk.END)
        widget.config(state=tk.DISABLED)
    widget.after(0, _do)


def run_pipeline(output, btn, status_lbl):
    """Full pipeline: install deps → detect hardware. Runs in a thread."""
    clear(output)
    set_status(status_lbl, "⏳ Vérification des dépendances...", WARN)
    set_btn(btn, "⏳ En cours...", tk.DISABLED)

    def log(msg):
        append(output, msg)

    log("══════════════════════════════════════\n")
    log("  BIZON — Initialisation\n")
    log("══════════════════════════════════════\n\n")

    # Step 1 — install
    log("📋 Vérification des dépendances...\n")
    ok = install_dependencies(log)

    if not ok:
        set_status(status_lbl, "❌ Erreur d'installation", ERR)
        set_btn(btn, "🚀 Lancer la Détection", tk.NORMAL)
        return

    # Step 2 — detect
    set_status(status_lbl, "🔍 Analyse du matériel...", WARN)
    try:
        report = detect_hardware(log)
        log("\n")
        log(format_report(report))
        set_status(status_lbl, "✅ Détection terminée", ACCENT)
    except Exception as e:
        log(f"\n❌ Erreur lors de la détection : {e}\n")
        set_status(status_lbl, "❌ Erreur lors de la détection", ERR)

    set_btn(btn, "🚀 Lancer la Détection", tk.NORMAL)


def on_button_click(output, btn, status_lbl):
    t = threading.Thread(target=run_pipeline, args=(output, btn, status_lbl), daemon=True)
    t.start()


def main():
    root = tk.Tk()
    root.title("Bizon — Test Matériel")
    root.geometry("700x650")
    root.resizable(True, True)
    root.configure(bg=DARK_BG)
    root.minsize(600, 500)

    title_font = font.Font(family="Helvetica", size=20, weight="bold")
    sub_font   = font.Font(family="Helvetica", size=11)
    mono_font  = font.Font(family="Courier", size=11)
    btn_font   = font.Font(family="Helvetica", size=13, weight="bold")
    small_font = font.Font(family="Helvetica", size=10)

    # Header
    header = tk.Frame(root, bg=DARK_BG)
    header.pack(fill=tk.X, padx=25, pady=(25, 5))
    tk.Label(header, text="🦬 Bizon", font=title_font, fg=ACCENT, bg=DARK_BG).pack(anchor="w")
    tk.Label(header, text="Détection locale du matériel & adaptation des paramètres",
             font=sub_font, fg=TEXT_DIM, bg=DARK_BG).pack(anchor="w")

    tk.Frame(root, height=1, bg=ACCENT, bd=0).pack(fill=tk.X, padx=25, pady=8)

    # Status
    status_lbl = tk.Label(root, text="En attente…", font=small_font, fg=TEXT_DIM, bg=DARK_BG)
    status_lbl.pack(anchor="w", padx=25)

    # Button
    btn_frame = tk.Frame(root, bg=DARK_BG)
    btn_frame.pack(fill=tk.X, padx=25, pady=10)

    btn = tk.Button(
        btn_frame,
        text="🚀 Lancer la Détection",
        font=btn_font,
        bg=ACCENT, fg="#0d1117",
        activebackground=BTN_ACT,
        relief=tk.FLAT,
        padx=20, pady=10,
        cursor="hand2", bd=0,
    )
    btn.pack(side=tk.LEFT)

    # Output
    output_frame = tk.Frame(root, bg=CARD_BG, bd=0)
    output_frame.pack(fill=tk.BOTH, expand=True, padx=25, pady=(0, 10))

    output_txt = scrolledtext.ScrolledText(
        output_frame,
        font=mono_font,
        bg=CARD_BG, fg=TEXT,
        insertbackground=TEXT,
        relief=tk.FLAT,
        padx=14, pady=10,
        wrap=tk.NONE,
        state=tk.DISABLED,
    )
    output_txt.pack(fill=tk.BOTH, expand=True)
    append(output_txt,
           "Cliquez sur le bouton pour détecter le matériel.\n"
           "Les dépendances (psutil, torch) seront installées automatiquement si nécessaire.\n"
           "torch permet la détection GPU (CUDA pour NVIDIA, MPS pour Apple Silicon).\n")

    btn.config(command=lambda: on_button_click(output_txt, btn, status_lbl))

    # Footer
    tk.Label(root, text="Projet Olympus — Module Bizon · ECE Paris 2026",
             font=small_font, fg=TEXT_DIM, bg=DARK_BG).pack(pady=(0, 8))

    root.mainloop()


if __name__ == "__main__":
    main()
