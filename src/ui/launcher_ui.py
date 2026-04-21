import tkinter as tk
from tkinter import scrolledtext, font
import platform
import threading
import sys
import logging
from src.hardware.detector import detect_hardware

# Configuration du logging
logger = logging.getLogger("LauncherUI")

# Palette de couleurs (Soft Theme)
BG        = "#F5EFE6"
CARD      = "#EDE0D0" 
BORDER    = "#C8B89A" 
ACCENT    = "#7A4E2D" 
ACCENT_H  = "#5C3820" 
TEXT      = "#2C1A0E" 
TEXT_DIM  = "#9E8070" 
SUCCESS   = "#4A7A4A" 
BTN_TXT   = "#FFFFFF"

class RoundedButton:
    def __init__(self, parent, text="", command=None, font_obj=None, radius=24):
        self.frame = tk.Frame(parent, bg=BG)
        self.canvas = tk.Canvas(self.frame, width=240, height=54, bg=BG, highlightthickness=0)
        self.canvas.pack(pady=10)
        
        self.text = text
        self.command = command
        self.font = font_obj
        self.radius = radius
        
        self.canvas.bind("<Enter>", lambda e: self._draw(ACCENT_H, shadow=True))
        self.canvas.bind("<Leave>", lambda e: self._draw(ACCENT, shadow=False))
        self.canvas.bind("<Button-1>", lambda e: self.command() if self.command else None)
        
        self._draw(ACCENT)
        
    def _draw(self, color, shadow=False):
        self.canvas.delete("all")
        w, h, r = 240, 54, self.radius
        
        # Shadow (simulated)
        if shadow:
            self.canvas.create_oval(10, h-10, w-10, h, fill="#D0C0B0", outline="")
            
        # Button Body
        self._draw_rounded_rect(2, 2, w-2, h-6, r, fill=color, outline="")
        
        self.canvas.create_text(w//2, (h-4)//2, text=self.text, fill=BTN_TXT, font=self.font)

    def set_processing(self):
        """Désactive le bouton et change le texte pour indiquer le chargement."""
        self.text = "LANCEMENT EN COURS..."
        self.canvas.unbind("<Button-1>")
        self.canvas.unbind("<Enter>")
        self.canvas.unbind("<Leave>")
        self._draw(SUCCESS) # Vert pour confirmer l'action

    def _draw_rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        points = [x1+r, y1, x1+r, y1, x2-r, y1, x2-r, y1, x2, y1, x2, y1+r, x2, y1+r, x2, y2-r, x2, y2-r, x2, y2, x2-r, y2, x2-r, y2, x1+r, y2, x1+r, y2, x1, y2, x1, y2-r, x1, y2-r, x1, y1+r, x1, y1+r, x1, y1]
        return self.canvas.create_polygon(points, smooth=True, **kwargs)

class LauncherUI:
    def __init__(self, on_launch_callback):
        self.root = tk.Tk()
        self.root.title("Cassandre Control Center")
        self.root.geometry("800x650")
        self.root.configure(bg=BG)
        self.on_launch_callback = on_launch_callback
        
        self.setup_ui()
        
    def setup_ui(self):
        # Fonts
        FAMILY = "Outfit" if platform.system() == "Darwin" else "Arial" 
        self.title_font = font.Font(family=FAMILY, size=28, weight="bold")
        self.sub_font = font.Font(family=FAMILY, size=11)
        self.btn_font = font.Font(family=FAMILY, size=13, weight="bold")
        self.mono_font = font.Font(family="Courier", size=11)
        
        # Header
        header = tk.Frame(self.root, bg=BG, padx=40, pady=30)
        header.pack(fill=tk.X)
        
        tk.Label(header, text="🔮 CASSANDRE", font=self.title_font, fg=ACCENT, bg=BG).pack(side=tk.LEFT)
        tk.Label(header, text="Terminal d'Intelligence Financière", font=self.sub_font, fg=TEXT_DIM, bg=BG).pack(side=tk.LEFT, padx=20, pady=(12, 0))
        
        # Area Container for "Glass" effect
        container = tk.Frame(self.root, bg=BORDER, padx=1, pady=1)
        container.pack(fill=tk.BOTH, expand=True, padx=40, pady=10)
        
        # Hardware Report Area
        self.report_area = scrolledtext.ScrolledText(container, bg=CARD, fg=TEXT, font=self.mono_font, relief=tk.FLAT, padx=25, pady=25)
        self.report_area.pack(fill=tk.BOTH, expand=True)
        
        # Footer / Action
        footer = tk.Frame(self.root, bg=BG, pady=30)
        footer.pack(fill=tk.X)
        
        self.launch_btn = RoundedButton(footer, text="LANCER LE TERMINAL", command=self.on_launch_callback, font_obj=self.btn_font)
        self.launch_btn.frame.pack(anchor="center")
        
        # Start hardware detection in background
        threading.Thread(target=self.run_detection, daemon=True).start()
        
    def _update_report(self, text):
        """Met à jour le widget tkinter depuis le thread principal (thread-safe)."""
        self.report_area.config(state=tk.NORMAL)
        self.report_area.delete(1.0, tk.END)
        self.report_area.insert(tk.END, text)
        self.report_area.config(state=tk.DISABLED)

    def run_detection(self):
        # Afficher le message initial via root.after pour rester thread-safe
        logger.info("[HARDWARE] Lancement de la détection...")
        self.root.after(0, lambda: self.report_area.insert(tk.END, "🔍 Analyse du matériel en cours...\n"))
        try:
            report = detect_hardware()
            logger.info(f"[HARDWARE] Détection terminée : {report['os']['system']} | {report['cpu']['cores_logical']} cores")
            text = "\n📋 RAPPORT CONFIGURATION CASSANDRE\n" + "═"*40 + "\n\n"
            text += f"  • SYSTÈME   : {report['os']['system']} {report['os']['machine']}\n"
            text += f"  • CPU       : {report['cpu']['cores_logical']} vCores ({report['cpu']['frequency_mhz']} MHz)\n"
            text += f"  • RAM       : {report['ram']['total_gb']} Go\n"
            text += f"  • GPU       : {report['gpu']['device']}\n\n"
            text += "✅ PROFIL D'ACCÉLÉRATION OPTIMISÉ\n"
            text += "────────────────────────────────────────\n"
            text += f"  → Batch Size      : {report['adaptation']['batch_size']}\n"
            text += f"  → Parallel Workers : {report['adaptation']['workers']}\n"
            text += f"  → Refresh Rate     : {report['adaptation']['calc_frequency_ms']}ms\n"
            text += "────────────────────────────────────────\n"
            logger.info("[UI] Mise à jour du rapport matériel sur l'interface.")
            self.root.after(0, lambda t=text: self._update_report(t))
        except Exception as e:
            logger.error(f"[HARDWARE] Erreur lors de la détection : {e}")
            self.root.after(0, lambda err=e: self.report_area.insert(tk.END, f"\n❌ Erreur : {err}"))

    def run(self):
        self.root.mainloop()

    def close(self):
        self.root.destroy()
