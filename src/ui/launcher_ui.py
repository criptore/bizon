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
    def __init__(self, parent, text="", command=None, font_obj=None, radius=22):
        self.frame = tk.Frame(parent, bg=BG)
        self.canvas = tk.Canvas(self.frame, width=220, height=45, bg=BG, highlightthickness=0)
        self.canvas.pack()
        
        self.text = text
        self.command = command
        self.font = font_obj
        self.radius = radius
        
        self.canvas.bind("<Enter>", lambda e: self._draw(ACCENT_H))
        self.canvas.bind("<Leave>", lambda e: self._draw(ACCENT))
        self.canvas.bind("<Button-1>", lambda e: self.command() if self.command else None)
        
        self._draw(ACCENT)
        
    def _draw(self, color):
        self.canvas.delete("all")
        w, h, r = 220, 45, self.radius
        points = [r, 0, w-r, 0, w, 0, w, r, w, h-r, w, h, w-r, h, r, h, 0, h, 0, h-r, 0, r, 0, 0]
        self.canvas.create_polygon(points, smooth=True, fill=color, outline="")
        self.canvas.create_text(w//2, h//2, text=self.text, fill=BTN_TXT, font=self.font)

class LauncherUI:
    def __init__(self, on_launch_callback):
        self.root = tk.Tk()
        self.root.title("Bizon Control Center")
        self.root.geometry("700x600")
        self.root.configure(bg=BG)
        self.on_launch_callback = on_launch_callback
        
        self.setup_ui()
        
    def setup_ui(self):
        # Fonts
        FAMILY = "Arial" # Fallback if Acumin Wide not found
        self.title_font = font.Font(family=FAMILY, size=24, weight="bold")
        self.btn_font = font.Font(family=FAMILY, size=12, weight="bold")
        self.mono_font = font.Font(family="Courier", size=10)
        
        # Header
        header = tk.Frame(self.root, bg=BG, padx=30, pady=20)
        header.pack(fill=tk.X)
        
        tk.Label(header, text="🦬 BIZON", font=self.title_font, fg=ACCENT, bg=BG).pack(side=tk.LEFT)
        tk.Label(header, text="Central Control", font=font.Font(family=FAMILY, size=12), fg=TEXT_DIM, bg=BG).pack(side=tk.LEFT, padx=15, pady=(10, 0))
        
        # Hardware Report Area
        self.report_area = scrolledtext.ScrolledText(self.root, bg=CARD, fg=TEXT, font=self.mono_font, relief=tk.FLAT, padx=20, pady=20)
        self.report_area.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        # Footer / Action
        footer = tk.Frame(self.root, bg=BG, pady=20)
        footer.pack(fill=tk.X)
        
        self.launch_btn = RoundedButton(footer, text="LANCER LE TERMINAL", command=self.on_launch_callback, font_obj=self.btn_font)
        self.launch_btn.frame.pack(anchor="center")
        
        # Start hardware detection in background
        threading.Thread(target=self.run_detection, daemon=True).start()
        
    def _update_report(self, text):
        """Met à jour le widget tkinter depuis le thread principal (thread-safe)."""
        self.report_area.delete(1.0, tk.END)
        self.report_area.insert(tk.END, text)

    def run_detection(self):
        # Afficher le message initial via root.after pour rester thread-safe
        self.root.after(0, lambda: self.report_area.insert(tk.END, "🔍 Analyse du matériel en cours...\n"))
        try:
            report = detect_hardware()
            text = "\n📋 RAPPORT CONFIGURATION\n" + "═"*30 + "\n"
            text += f"Système : {report['os']['system']} {report['os']['machine']}\n"
            text += f"CPU     : {report['cpu']['cores_logical']} cœurs ({report['cpu']['frequency_mhz']} MHz)\n"
            text += f"RAM     : {report['ram']['total_gb']} Go\n"
            text += f"GPU     : {report['gpu']['device']}\n\n"
            text += "✅ Profil Bizon optimisé :\n"
            text += f" → Batch Size : {report['adaptation']['batch_size']}\n"
            text += f" → Workers : {report['adaptation']['workers']}\n"
            text += f" → Fréquence : {report['adaptation']['calc_frequency_ms']}ms\n"
            self.root.after(0, lambda t=text: self._update_report(t))
        except Exception as e:
            self.root.after(0, lambda err=e: self.report_area.insert(tk.END, f"\n❌ Erreur : {err}"))

    def run(self):
        self.root.mainloop()

    def close(self):
        self.root.destroy()
