import subprocess
import sys
import importlib.util
import json
import tkinter as tk
from tkinter import scrolledtext

# 1. auto-installation des dépendances
def ensure_dependencies():
    print("Vérification des dépendances...")
    required = ["psutil"]
    missing = [pkg for pkg in required if importlib.util.find_spec(pkg) is None]
    
    if missing:
        print(f"[!] Installation des paquets manquants : {', '.join(missing)}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
        print("Installation terminée.")
    else:
        print("Les dépendances sont déjà présentes. Pas de réinstallation.")

def start_detect(text_widget):
    # Désactiver le text widget brièvement pour le vider
    text_widget.config(state=tk.NORMAL)
    text_widget.delete(1.0, tk.END)
    text_widget.insert(tk.END, "Scan du système en cours, veuillez patienter...\n")
    text_widget.update()
    
    try:
        # Ajout du chemin pour importer le module Bizon
        import os
        sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
        
        from src.hardware.detector import detect_hardware
        
        hw_report = detect_hardware()
        report_json = json.dumps(hw_report, indent=4)
        
        text_widget.delete(1.0, tk.END)
        text_widget.insert(tk.END, report_json)
    except Exception as e:
        text_widget.delete(1.0, tk.END)
        text_widget.insert(tk.END, f"Une erreur s'est produite lors de la détection :\n{e}")
        
    text_widget.config(state=tk.DISABLED)

def main():
    # S'assure que psutil est là avant de lancer l'interface
    try:
        ensure_dependencies()
    except Exception as e:
        print(f"Erreur d'installation PIP: {e}")
    
    # 2. Création de l'interface visuelle avec Tkinter
    root = tk.Tk()
    root.title("Prise en main - Détection Bizon")
    root.geometry("600x550")
    
    # Titre
    lbl_title = tk.Label(root, text="🦬 Bizon - Détection Matérielle", font=("Arial", 16, "bold"))
    lbl_title.pack(pady=15)
    
    # Instructions
    lbl_desc = tk.Label(root, text="Cliquez sur le bouton pour scanner le CPU, la RAM et le GPU.\n"
                                   "Si c'est la première fois, l'application installera les paquets automatiquement.",
                        font=("Arial", 10), fg="#555")
    lbl_desc.pack(pady=5)
    
    # Bouton
    btn = tk.Button(root, text="🚀 Lancer la Détection", font=("Arial", 14), width=20, bg="#4CAF50",
                    command=lambda: start_detect(txt_output))
    btn.pack(pady=15)
    
    # Zone de texte de résultats
    txt_output = scrolledtext.ScrolledText(root, width=65, height=20, font=("Courier", 11), bg="#f4f4f4")
    txt_output.pack(pady=10)
    txt_output.insert(tk.END, "En attente du lancement...")
    txt_output.config(state=tk.DISABLED) # Lecture seule par défaut
    
    # Lancement de l'app
    root.mainloop()

if __name__ == "__main__":
    main()
